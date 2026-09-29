import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import PodcastSetup from './PodcastSetup'
import * as podcasts from '../services/podcastsApi'
import { catalog, episode, preferences } from './podcastPageFixtures.test.utils'

vi.mock('../services/podcastsApi')

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => ({
  ...(await vi.importActual<typeof import('react-router-dom')>('react-router-dom')),
  useNavigate: () => mockNavigate,
}))

const renderSetup = (search = '?show=weekend-food-talk') =>
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter initialEntries={[`/podcasts/setup${search}`]}>
        <PodcastSetup />
      </MemoryRouter>
    </QueryClientProvider>,
  )

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(podcasts.getPodcastCatalog).mockResolvedValue(catalog)
  vi.mocked(podcasts.getPodcastPreferences).mockResolvedValue(preferences)
  vi.mocked(podcasts.startEpisode).mockResolvedValue(episode())
})

describe('PodcastSetup page', () => {
  it('shows the show, its hosts and the learners role', async () => {
    renderSetup()

    expect(await screen.findByRole('heading', { name: 'Weekend Food Talk' })).toBeInTheDocument()
    expect(screen.getByText('Lucía')).toBeInTheDocument()
    expect(screen.getByText('Marco')).toBeInTheDocument()
  })

  it('starts on the last format and the default length', async () => {
    renderSetup()

    await waitFor(() => expect(screen.getByRole('radio', { name: /Panel/ })).toBeChecked())
    expect(screen.getByRole('radio', { name: /Medium/ })).toBeChecked()
  })

  it('prefills the learners name', async () => {
    renderSetup()

    await waitFor(() => expect(screen.getByLabelText(/Your name/)).toHaveValue('Sam'))
  })

  it('starts the episode with the chosen options and opens it', async () => {
    renderSetup()
    await waitFor(() => expect(screen.getByRole('radio', { name: /Panel/ })).toBeChecked())
    fireEvent.click(screen.getByRole('radio', { name: /One host/ }))
    fireEvent.click(screen.getByRole('radio', { name: /Short/ }))

    fireEvent.click(screen.getByRole('button', { name: 'Start episode' }))

    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/podcasts/episodes/57'))
    expect(podcasts.startEpisode).toHaveBeenCalledWith({
      show: catalog.shows[0],
      format: 'one_host',
      length: 'short',
      learner_name: 'Sam',
    })
  })

  it('shows why an episode could not start', async () => {
    vi.mocked(podcasts.startEpisode).mockRejectedValue(new Error('The practice language changed. Pick the show again.'))
    renderSetup()
    await screen.findByRole('heading', { name: 'Weekend Food Talk' })

    fireEvent.click(screen.getByRole('button', { name: 'Start episode' }))

    expect(await screen.findByText('The practice language changed. Pick the show again.')).toBeInTheDocument()
  })

  it('returns to Podcasts with a message for an unknown show', async () => {
    renderSetup('?show=missing')

    await waitFor(() =>
      expect(mockNavigate).toHaveBeenCalledWith('/podcasts', {
        replace: true,
        state: { message: expect.stringMatching(/isn't available/) },
      }),
    )
  })
})

describe('PodcastSetup page — voice notices (spec edge case)', () => {
  const withVoices = (voices: Partial<typeof catalog.voices>) => ({ ...catalog, voices: { ...catalog.voices, ...voices } })

  it('says the hosts share one voice when a two-host format is chosen', async () => {
    vi.mocked(podcasts.getPodcastCatalog).mockResolvedValue(withVoices({ installed_count: 1, shared_voice_notice: 'Both hosts will share one voice.' }))
    renderSetup()

    await waitFor(() => expect(screen.getByRole('radio', { name: /Panel/ })).toBeChecked())

    expect(screen.getByRole('status')).toHaveTextContent('Both hosts will share one voice.')
    fireEvent.click(screen.getByRole('radio', { name: /One host/ }))
    expect(screen.queryByText('Both hosts will share one voice.')).not.toBeInTheDocument()
  })

  it('says when no voice is installed', async () => {
    vi.mocked(podcasts.getPodcastCatalog).mockResolvedValue(withVoices({ installed_count: 0, unavailable_message: 'No Spanish voice is installed.' }))

    renderSetup()

    expect(await screen.findByText('No Spanish voice is installed.')).toBeInTheDocument()
  })
})
