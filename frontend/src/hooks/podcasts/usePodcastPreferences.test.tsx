import { renderHook, waitFor, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as podcasts from '../../services/podcastsApi'
import type { PodcastPreferences } from '../../services/podcastsApi'
import { usePodcastPreferences } from './usePodcastPreferences'
import { queryWrapper } from './queryWrapper.test.utils'

vi.mock('../../services/podcastsApi')

const stored: PodcastPreferences = {
  last_format: 'panel',
  is_show_text_on: false,
  interests: [],
  learner_name: 'Sam',
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('usePodcastPreferences', () => {
  it('serves the stored preferences', async () => {
    vi.mocked(podcasts.getPodcastPreferences).mockResolvedValue(stored)
    const { wrapper } = queryWrapper()

    const { result } = renderHook(() => usePodcastPreferences(), { wrapper })

    await waitFor(() => expect(result.current.preferences).toEqual(stored))
  })

  it('saves a change and serves the saved values', async () => {
    vi.mocked(podcasts.getPodcastPreferences).mockResolvedValue(stored)
    vi.mocked(podcasts.updatePodcastPreferences).mockResolvedValue({ ...stored, is_show_text_on: true })
    const { wrapper } = queryWrapper()
    const { result } = renderHook(() => usePodcastPreferences(), { wrapper })
    await waitFor(() => expect(result.current.preferences).toBeDefined())

    await act(async () => result.current.update({ is_show_text_on: true }))

    expect(podcasts.updatePodcastPreferences).toHaveBeenCalledWith({ is_show_text_on: true })
    await waitFor(() => expect(result.current.preferences?.is_show_text_on).toBe(true))
  })

  it('reports a failed save', async () => {
    vi.mocked(podcasts.getPodcastPreferences).mockResolvedValue(stored)
    vi.mocked(podcasts.updatePodcastPreferences).mockRejectedValue(new Error('Too many interests.'))
    const { wrapper } = queryWrapper()
    const { result } = renderHook(() => usePodcastPreferences(), { wrapper })
    await waitFor(() => expect(result.current.preferences).toBeDefined())

    await act(async () => result.current.update({ interests: ['a'] }))

    await waitFor(() => expect(result.current.saveError).toBe('Too many interests.'))
  })
})
