import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import * as podcasts from '../../services/podcastsApi'
import { catalog } from '../../pages/podcastPageFixtures.test.utils'
import { queryWrapper } from '../../hooks/podcasts/queryWrapper.test.utils'
import { generatedShow, seriesListing } from './fixtures.test.utils'
import MyShows from './MyShows'

vi.mock('../../services/podcastsApi')

const kept = { ...generatedShow, saved_show_id: 9, is_favourite: false, series: null }

const renderMine = (myShows = [seriesListing, kept]) => {
  const onChoose = vi.fn()
  render(<MyShows catalog={{ ...catalog, my_shows: myShows }} onChoose={onChoose} onToggleFavourite={vi.fn()} />, { wrapper: queryWrapper().wrapper })
  return onChoose
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(podcasts.removeShow).mockResolvedValue(undefined)
})

describe('MyShows', () => {
  it('is a labelled region listing each show with its next episode', () => {
    renderMine()

    const region = screen.getByRole('region', { name: 'My shows' })
    expect(region).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Big Little Questions' })).toHaveAccessibleDescription(/Episode 2 next/)
  })

  it('says episode 1 is next for a show with no series yet', () => {
    renderMine()

    const card = screen.getByRole('button', { name: 'Night Shift Abroad' })
    expect(card).toHaveAccessibleDescription(/Episode 1 next\./)
    expect(card).toHaveTextContent('Episode 1 next')
  })

  it('is hidden when empty', () => {
    renderMine([])

    expect(screen.queryByRole('region', { name: 'My shows' })).not.toBeInTheDocument()
  })

  it('offers Remove on a kept learner-made show only', () => {
    renderMine()

    expect(screen.getByRole('button', { name: 'Remove Night Shift Abroad' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Remove Big Little Questions' })).not.toBeInTheDocument()
  })

  it('asks before removing, and Cancel sends nothing', async () => {
    renderMine()

    await userEvent.click(screen.getByRole('button', { name: 'Remove Night Shift Abroad' }))
    expect(screen.getByRole('alertdialog')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(podcasts.removeShow).not.toHaveBeenCalled()
  })

  it('removes the show once confirmed', async () => {
    renderMine()

    await userEvent.click(screen.getByRole('button', { name: 'Remove Night Shift Abroad' }))
    await userEvent.click(screen.getByRole('button', { name: 'Remove' }))

    await waitFor(() => expect(podcasts.removeShow).toHaveBeenCalledWith(9))
  })
})
