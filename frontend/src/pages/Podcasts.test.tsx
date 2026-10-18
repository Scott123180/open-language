import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import Podcasts from './Podcasts'
import * as podcasts from '../services/podcastsApi'
import { catalog, preferences } from './podcastPageFixtures.test.utils'
import { generatedShow } from '../components/podcasts/fixtures.test.utils'

vi.mock('../services/podcastsApi')

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => ({
  ...(await vi.importActual<typeof import('react-router-dom')>('react-router-dom')),
  useNavigate: () => mockNavigate,
}))

const renderPodcasts = (state?: unknown) =>
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter initialEntries={[{ pathname: '/podcasts', state }]}>
        <Podcasts />
      </MemoryRouter>
    </QueryClientProvider>,
  )

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(podcasts.getPodcastCatalog).mockResolvedValue(catalog)
  vi.mocked(podcasts.getPodcastPreferences).mockResolvedValue(preferences)
})

describe('Podcasts page', () => {
  it('lists a card for every show in the catalogue', async () => {
    renderPodcasts()

    expect(await screen.findByRole('button', { name: 'Weekend Food Talk' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Podcasts' })).toBeInTheDocument()
  })

  it('opens the setup screen for the chosen show', async () => {
    renderPodcasts()

    fireEvent.click(await screen.findByRole('button', { name: 'Weekend Food Talk' }))

    expect(mockNavigate).toHaveBeenCalledWith('/podcasts/setup?show=weekend-food-talk')
  })

  it('shows a message passed from the setup screen', async () => {
    renderPodcasts({ message: "That show isn't available. Pick another one." })

    expect(await screen.findByText("That show isn't available. Pick another one.")).toBeInTheDocument()
  })

  it('explains a catalogue that could not load', async () => {
    vi.mocked(podcasts.getPodcastCatalog).mockRejectedValue(new Error('The shows could not be loaded.'))

    renderPodcasts()

    expect(await screen.findByText('The shows could not be loaded.')).toBeInTheDocument()
  })
})

describe('Podcasts page — generator and Surprise me (US4)', () => {
  it('opens setup with the generated draft', async () => {
    vi.mocked(podcasts.generateShow).mockResolvedValue(generatedShow)
    renderPodcasts()

    fireEvent.change(await screen.findByLabelText('Your show idea'), { target: { value: 'living abroad as a nurse' } })
    fireEvent.click(screen.getByRole('button', { name: 'Generate' }))

    await waitFor(() =>
      expect(mockNavigate).toHaveBeenCalledWith('/podcasts/setup', {
        state: { draft: generatedShow, idea: 'living abroad as a nurse', previousTitles: [] },
      }),
    )
  })

  it('opens setup with a surprise draft', async () => {
    const surprise = { ...generatedShow, source: 'surprise' as const }
    vi.mocked(podcasts.surpriseShow).mockResolvedValue(surprise)
    renderPodcasts()

    fireEvent.click(await screen.findByRole('button', { name: 'Surprise me' }))

    await waitFor(() =>
      expect(mockNavigate).toHaveBeenCalledWith('/podcasts/setup', { state: { draft: surprise, idea: null, previousTitles: [] } }),
    )
  })

  it('shows a declined idea and stays put', async () => {
    vi.mocked(podcasts.generateShow).mockRejectedValue(new Error("That idea can't become a show here. Try a different topic, or press Surprise me."))
    renderPodcasts()

    fireEvent.change(await screen.findByLabelText('Your show idea'), { target: { value: 'something nasty' } })
    fireEvent.click(screen.getByRole('button', { name: 'Generate' }))

    expect(await screen.findByRole('alert')).toHaveTextContent("That idea can't become a show here.")
    expect(mockNavigate).not.toHaveBeenCalled()
  })

  it('saves the learners interests', async () => {
    vi.mocked(podcasts.updatePodcastPreferences).mockResolvedValue({ ...preferences, interests: ['football', 'cooking'] })
    renderPodcasts()
    fireEvent.click(await screen.findByText('Your interests'))

    fireEvent.change(screen.getByLabelText(/Interests/), { target: { value: 'football, cooking' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save interests' }))

    await waitFor(() => expect(podcasts.updatePodcastPreferences).toHaveBeenCalledWith({ interests: ['football', 'cooking'] }))
  })
})

describe('Podcasts page — My shows (010 US4)', () => {
  it('lists My shows above the ready-made shows', async () => {
    const mine = { ...catalog.shows[0], show_id: 'game-day', title: 'Game Day', is_favourite: true }
    vi.mocked(podcasts.getPodcastCatalog).mockResolvedValue({ ...catalog, my_shows: [mine] })
    renderPodcasts()

    const region = await screen.findByRole('region', { name: 'My shows' })
    const readyMade = screen.getByRole('button', { name: 'Weekend Food Talk' })
    expect(region.compareDocumentPosition(readyMade) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('opens a kept learner-made show by its saved id', async () => {
    const kept = { ...generatedShow, saved_show_id: 9, is_favourite: true, series: null }
    vi.mocked(podcasts.getPodcastCatalog).mockResolvedValue({ ...catalog, my_shows: [kept] })
    renderPodcasts()

    fireEvent.click(await screen.findByRole('button', { name: 'Night Shift Abroad' }))

    expect(mockNavigate).toHaveBeenCalledWith('/podcasts/setup?saved=9')
  })
})

describe('Podcasts page — Find a new show (010 US5)', () => {
  it('opens a suggestion in setup with its draft', async () => {
    const suggestion = { ...generatedShow, source: 'suggested' as const, title: 'Plant Parents' }
    vi.mocked(podcasts.discoverShows).mockResolvedValue([suggestion, { ...suggestion, title: 'B' }, { ...suggestion, title: 'C' }])
    renderPodcasts()

    fireEvent.click(await screen.findByRole('button', { name: 'Find a new show' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Plant Parents' }))

    expect(mockNavigate).toHaveBeenCalledWith('/podcasts/setup', { state: { draft: suggestion, idea: null, previousTitles: [] } })
  })
})
