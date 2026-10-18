import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import * as podcasts from '../../services/podcastsApi'
import { catalog } from '../../pages/podcastPageFixtures.test.utils'
import FindNewShow from './FindNewShow'
import { suggestions } from './fixtures.test.utils'

vi.mock('../../services/podcastsApi')

const renderFinder = (shown = catalog) => {
  const props = { catalog: shown, onChoose: vi.fn(), onToggleFavourite: vi.fn() }
  render(<FindNewShow {...props} />)
  return props
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('FindNewShow', () => {
  it('shows progress in a polite live region, then the suggestions as cards', async () => {
    let finish: (value: podcasts.ShowDraft[]) => void = () => undefined
    vi.mocked(podcasts.discoverShows).mockReturnValue(new Promise((resolve) => { finish = resolve }))
    renderFinder()

    fireEvent.click(screen.getByRole('button', { name: 'Find a new show' }))

    const live = screen.getByText('Finding new shows…').closest('[aria-live]')
    expect(live).toHaveAttribute('aria-live', 'polite')
    finish(suggestions)
    expect(await screen.findByRole('button', { name: 'Night Trains of Europe' })).toHaveAccessibleDescription(/Topic: night trains/)
    expect(screen.getByRole('button', { name: 'Favourite Plant Parents' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Show me others' })).toBeInTheDocument()
  })

  it('opens a chosen suggestion in setup', async () => {
    vi.mocked(podcasts.discoverShows).mockResolvedValue(suggestions)
    const props = renderFinder()
    fireEvent.click(screen.getByRole('button', { name: 'Find a new show' }))

    fireEvent.click(await screen.findByRole('button', { name: 'Plant Parents' }))

    expect(props.onChoose).toHaveBeenCalledWith(suggestions[1])
  })

  it('favourites a suggestion', async () => {
    vi.mocked(podcasts.discoverShows).mockResolvedValue(suggestions)
    const props = renderFinder()
    fireEvent.click(screen.getByRole('button', { name: 'Find a new show' }))

    fireEvent.click(await screen.findByRole('button', { name: 'Favourite Board Game Night' }))

    expect(props.onToggleFavourite).toHaveBeenCalledWith(expect.objectContaining({ title: 'Board Game Night' }))
  })

  it('unfavourites a kept suggestion by its saved show', async () => {
    vi.mocked(podcasts.discoverShows).mockResolvedValue(suggestions)
    const kept = { ...suggestions[2], saved_show_id: 31, is_favourite: true, series: null }
    const props = renderFinder({ ...catalog, my_shows: [kept] })
    fireEvent.click(screen.getByRole('button', { name: 'Find a new show' }))

    fireEvent.click(await screen.findByRole('button', { name: 'Favourite Board Game Night', pressed: true }))

    expect(props.onToggleFavourite).toHaveBeenCalledWith(expect.objectContaining({ saved_show_id: 31, is_favourite: true }))
  })

  it('shows the plain message when no shows came, and stays usable', async () => {
    vi.mocked(podcasts.discoverShows).mockRejectedValueOnce(new Error('Ollama is not running.'))
    renderFinder()

    fireEvent.click(screen.getByRole('button', { name: 'Find a new show' }))

    expect(await screen.findByText('Ollama is not running.')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Find a new show' })).toBeEnabled())
  })
})
