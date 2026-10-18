import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import * as podcasts from '../../services/podcastsApi'
import { seriesDetail } from '../../components/podcasts/fixtures.test.utils'
import { queryWrapper } from './queryWrapper.test.utils'
import { PODCAST_CATALOG_KEY } from './usePodcastCatalog'
import { seriesKey } from './useSeries'
import { useRecast } from './useRecast'

vi.mock('../../services/podcastsApi')

beforeEach(() => {
  vi.clearAllMocks()
})

describe('useRecast', () => {
  it('posts the recast and refreshes the series and the catalogue', async () => {
    const recast = seriesDetail({ hosts: [seriesDetail().hosts[0], { ...seriesDetail().hosts[1], name: 'Pablo' }] })
    vi.mocked(podcasts.recastHost).mockResolvedValue(recast)
    const { client, wrapper } = queryWrapper()
    const invalidate = vi.spyOn(client, 'invalidateQueries')
    const { result } = renderHook(() => useRecast(4, 'es', 'Sam'), { wrapper })

    await act(() => result.current.recast('second', 'joker'))

    expect(podcasts.recastHost).toHaveBeenCalledWith(4, 'second', { language: 'es', learner_name: 'Sam', personality_id: 'joker' })
    expect(client.getQueryData(seriesKey(4))).toEqual(recast)
    expect(invalidate).toHaveBeenCalledWith({ queryKey: PODCAST_CATALOG_KEY })
  })

  it('keeps the server’s words when a recast is refused', async () => {
    vi.mocked(podcasts.recastHost).mockRejectedValue(new Error('Hugo already has that personality. Pick another one.'))
    const { result } = renderHook(() => useRecast(4, 'es', ''), { wrapper: queryWrapper().wrapper })

    await act(() => result.current.recast('second', 'curious_interviewer'))

    await waitFor(() => expect(result.current.error).toBe('Hugo already has that personality. Pick another one.'))
  })
})
