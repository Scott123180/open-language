import { renderHook, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as podcasts from '../../services/podcastsApi'
import { queryWrapper } from './queryWrapper.test.utils'
import { seriesDetail } from '../../components/podcasts/fixtures.test.utils'
import { useSeries } from './useSeries'

vi.mock('../../services/podcastsApi')

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(podcasts.getSeries).mockResolvedValue(seriesDetail())
  vi.mocked(podcasts.catchUpSeriesMemory).mockResolvedValue({ status: 'started' })
})

describe('useSeries', () => {
  it('reads the series detail', async () => {
    const { result } = renderHook(() => useSeries(4), { wrapper: queryWrapper().wrapper })

    await waitFor(() => expect(result.current.detail?.series_id).toBe(4))
    expect(podcasts.getSeries).toHaveBeenCalledWith(4)
  })

  it('starts a memory catch-up once when the setup opens', async () => {
    const { result, rerender } = renderHook(() => useSeries(4), { wrapper: queryWrapper().wrapper })

    await waitFor(() => expect(result.current.detail).toBeDefined())
    rerender()

    expect(podcasts.catchUpSeriesMemory).toHaveBeenCalledTimes(1)
    expect(podcasts.catchUpSeriesMemory).toHaveBeenCalledWith(4)
  })

  it('reads nothing without a series', () => {
    const { result } = renderHook(() => useSeries(null), { wrapper: queryWrapper().wrapper })

    expect(result.current.detail).toBeUndefined()
    expect(podcasts.getSeries).not.toHaveBeenCalled()
    expect(podcasts.catchUpSeriesMemory).not.toHaveBeenCalled()
  })
})
