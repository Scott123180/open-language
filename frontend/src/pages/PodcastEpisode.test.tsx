import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import PodcastEpisode from './PodcastEpisode'
import * as api from '../services/api'
import * as podcasts from '../services/podcastsApi'
import { episode } from './podcastPageFixtures.test.utils'

vi.mock('../services/api')
vi.mock('../services/podcastsApi')

const mockStopRecording = vi.fn()
let isRecording = false
vi.mock('../hooks/useRecorder', () => ({
  useRecorder: () => ({ startRecording: vi.fn(), stopRecording: mockStopRecording, isRecording, error: null }),
}))

const renderEpisode = () =>
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter initialEntries={['/podcasts/episodes/57']}>
        <Routes>
          <Route path="/podcasts/episodes/:conversationId" element={<PodcastEpisode />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )

beforeEach(() => {
  vi.clearAllMocks()
  isRecording = false
  Element.prototype.scrollIntoView = vi.fn()
  HTMLMediaElement.prototype.pause = vi.fn()
  HTMLMediaElement.prototype.play = vi.fn(() => Promise.resolve())
  vi.mocked(api.getSettings).mockResolvedValue({ conversation_level: 'natural' } as api.AppSettings)
  vi.mocked(api.getConversationLevels).mockResolvedValue([])
  vi.mocked(podcasts.getEpisode).mockResolvedValue(episode())
  vi.mocked(podcasts.getPodcastPreferences).mockResolvedValue({ last_format: 'one_host', is_show_text_on: false, interests: [], learner_name: null })
  vi.mocked(podcasts.warmEpisodeSession).mockResolvedValue(undefined)
  vi.mocked(podcasts.streamEpisodeMessage).mockResolvedValue(undefined)
  vi.mocked(api.transcribeAudio).mockResolvedValue({ text: 'Hallo', detected_language: 'de', confidence: 0.9, is_low_confidence: false })
  mockStopRecording.mockResolvedValue(new Blob(['audio']))
})

describe('PodcastEpisode page — One host', () => {
  it('shows the show and the host line with its speaker', async () => {
    renderEpisode()

    expect(await screen.findByText('¡Bienvenidos! ¿Qué cocinaste?')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Weekend Food Talk' })).toBeInTheDocument()
    expect(screen.getAllByText('Lucía').length).toBeGreaterThan(0)
    expect(screen.getByText('Your turn')).toBeInTheDocument()
  })

  it('offers the input bar, suggestions and the helper at the learners turn', async () => {
    renderEpisode()

    expect(await screen.findByLabelText('Type a message')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /start recording/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /suggest/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /expression helper/i })).toBeInTheDocument()
  })

  it('sends a typed reply', async () => {
    renderEpisode()
    fireEvent.change(await screen.findByLabelText('Type a message'), { target: { value: 'Paella' } })

    fireEvent.click(screen.getByRole('button', { name: 'Send message' }))

    await waitFor(() =>
      expect(podcasts.streamEpisodeMessage).toHaveBeenCalledWith(
        57,
        { content: 'Paella', input_source: 'keyboard', transcription_confidence: undefined },
        expect.anything(),
      ),
    )
  })

  it('transcribes a recording in the episodes language, not the setting', async () => {
    isRecording = true
    renderEpisode()

    fireEvent.click(await screen.findByRole('button', { name: 'Stop recording' }))

    await waitFor(() => expect(api.transcribeAudio).toHaveBeenCalledWith(expect.any(Blob), 'de'))
    await waitFor(() =>
      expect(podcasts.streamEpisodeMessage).toHaveBeenCalledWith(
        57,
        { content: 'Hallo', input_source: 'voice', transcription_confidence: 0.9 },
        expect.anything(),
      ),
    )
  })

  it('hides the input bar while the hosts speak', async () => {
    vi.mocked(podcasts.getEpisode).mockResolvedValue(episode({ turn: 'hosts', awaiting: 'continue' }))

    renderEpisode()

    expect(await screen.findByRole('button', { name: 'Continue' })).toBeInTheDocument()
    expect(screen.queryByLabelText('Type a message')).not.toBeInTheDocument()
  })

  it('shows a missing host voice and keeps the line readable', async () => {
    const hosts = [{ ...episode().hosts[0], is_voice_available: false, voice_unavailable_message: "Lucía's voice isn't installed." }]
    vi.mocked(podcasts.getEpisode).mockResolvedValue(episode({ hosts }))

    renderEpisode()

    expect(await screen.findByText("Lucía's voice isn't installed.")).toBeInTheDocument()
    expect(screen.getByText('¡Bienvenidos! ¿Qué cocinaste?')).toBeInTheDocument()
  })

  it('shows an error with a way to retry the line', async () => {
    vi.mocked(podcasts.getEpisode).mockResolvedValue(episode({ turn: 'hosts', awaiting: 'opening', lines: [] }))
    vi.mocked(podcasts.streamEpisodeNext)
      .mockImplementationOnce(async (_id, handlers) => handlers.onError('The AI is not responding.'))
      .mockImplementationOnce(async (_id, handlers) => {
        handlers.onLine({ event: 'line', line: episode().lines[0], turn: 'learner', awaiting: null })
        handlers.onDone({ done: true, turn: 'learner', awaiting: null })
      })
    renderEpisode()
    expect(await screen.findByText('The AI is not responding.')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))

    await waitFor(() => expect(podcasts.streamEpisodeNext).toHaveBeenCalledTimes(2))
  })
})

describe('PodcastEpisode page — Listen', () => {
  const listen = () =>
    episode({ format: 'listen', format_label: 'Listen', turn: 'hosts', awaiting: 'continue', lines: [{ ...episode().lines[0], invites_learner: false }] })

  it('has no input bar, a Show text switch, and Continue as the only primary action', async () => {
    vi.mocked(podcasts.getEpisode).mockResolvedValue(listen())

    renderEpisode()

    expect(await screen.findByRole('button', { name: 'Continue' })).toBeInTheDocument()
    expect(screen.getByRole('switch', { name: 'Show text' })).toBeInTheDocument()
    expect(screen.queryByLabelText('Type a message')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /start recording/i })).not.toBeInTheDocument()
  })

  it('hides the words of a line until it is tapped', async () => {
    vi.mocked(podcasts.getEpisode).mockResolvedValue(listen())
    vi.mocked(podcasts.revealLine).mockResolvedValue(undefined)
    renderEpisode()

    fireEvent.click(await screen.findByRole('button', { name: "Show Lucía's line" }))

    expect(screen.getByText('¡Bienvenidos! ¿Qué cocinaste?')).toBeInTheDocument()
    expect(podcasts.revealLine).toHaveBeenCalledWith(57, 901)
  })

  it('shows every line when Show text is on and saves the choice', async () => {
    vi.mocked(podcasts.getEpisode).mockResolvedValue(listen())
    vi.mocked(podcasts.updatePodcastPreferences).mockResolvedValue({ last_format: 'listen', is_show_text_on: true, interests: [], learner_name: null })
    renderEpisode()

    fireEvent.click(await screen.findByRole('switch', { name: 'Show text' }))

    expect(await screen.findByText('¡Bienvenidos! ¿Qué cocinaste?')).toBeInTheDocument()
    expect(podcasts.updatePodcastPreferences).toHaveBeenCalledWith({ is_show_text_on: true })
  })
})
