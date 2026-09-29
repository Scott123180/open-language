import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import Podcasts from './Podcasts'
import * as podcasts from '../services/podcastsApi'
import { catalog } from './podcastPageFixtures.test.utils'

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
