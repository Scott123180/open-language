import { renderHook, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as podcasts from '../../services/podcastsApi'
import type { PodcastCatalog } from '../../services/podcastsApi'
import { usePodcastCatalog } from './usePodcastCatalog'
import { queryWrapper } from './queryWrapper.test.utils'

vi.mock('../../services/podcastsApi')

const catalog = { language: 'es', shows: [{ show_id: 'weekend-food-talk' }] } as PodcastCatalog

beforeEach(() => {
  vi.clearAllMocks()
})

describe('usePodcastCatalog', () => {
  it('serves the catalogue', async () => {
    vi.mocked(podcasts.getPodcastCatalog).mockResolvedValue(catalog)
    const { wrapper } = queryWrapper()

    const { result } = renderHook(() => usePodcastCatalog(), { wrapper })

    await waitFor(() => expect(result.current.catalog).toEqual(catalog))
    expect(result.current.error).toBeNull()
  })

  it('reports a failure in plain words', async () => {
    vi.mocked(podcasts.getPodcastCatalog).mockRejectedValue(new Error('down'))
    const { wrapper } = queryWrapper()

    const { result } = renderHook(() => usePodcastCatalog(), { wrapper })

    await waitFor(() => expect(result.current.error).toBe('down'))
  })
})
