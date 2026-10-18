import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import * as podcasts from '../../services/podcastsApi'
import type { PodcastCatalog } from '../../services/podcastsApi'
import { catalog } from '../../pages/podcastPageFixtures.test.utils'
import { queryWrapper } from './queryWrapper.test.utils'
import { PODCAST_CATALOG_KEY } from './usePodcastCatalog'
import { FAVOURITE_FAILED, useFavourite } from './useFavourite'

vi.mock('../../services/podcastsApi')

const show = catalog.shows[0]

beforeEach(() => {
  vi.clearAllMocks()
})

const setup = () => {
  const { client, wrapper } = queryWrapper()
  client.setQueryData(PODCAST_CATALOG_KEY, catalog)
  const { result } = renderHook(() => useFavourite(), { wrapper })
  const cached = () => client.getQueryData<PodcastCatalog>(PODCAST_CATALOG_KEY)!
  return { result, cached }
}

describe('useFavourite', () => {
  it('marks the show at once and sends the change', async () => {
    let finish: (value: podcasts.ShowListing | null) => void = () => undefined
    vi.mocked(podcasts.setFavourite).mockReturnValue(new Promise((resolve) => { finish = resolve }))
    const { result, cached } = setup()

    act(() => result.current.toggle(show))

    await waitFor(() => expect(cached().shows[0].is_favourite).toBe(true))
    expect(podcasts.setFavourite).toHaveBeenCalledWith(show, true)
    await act(async () => finish({ ...show, is_favourite: true }))
  })

  it('rolls back with a plain message when the change fails', async () => {
    vi.mocked(podcasts.setFavourite).mockRejectedValue(new Error('HTTP 500'))
    const { result, cached } = setup()

    act(() => result.current.toggle(show))

    await waitFor(() => expect(result.current.error).toBe(FAVOURITE_FAILED))
    expect(cached().shows[0].is_favourite).toBe(false)
  })
})
