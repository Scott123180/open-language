import { act, renderHook } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import * as podcasts from '../../services/podcastsApi'
import { suggestions } from '../../components/podcasts/fixtures.test.utils'
import { useShowDiscovery } from './useShowDiscovery'

vi.mock('../../services/podcastsApi')

const others = suggestions.map((show) => ({ ...show, title: `${show.title} II` }))

beforeEach(() => {
  vi.clearAllMocks()
})

describe('useShowDiscovery', () => {
  it('finds new shows, then asks for others avoiding every title shown this visit', async () => {
    vi.mocked(podcasts.discoverShows).mockResolvedValueOnce(suggestions).mockResolvedValueOnce(others)
    const { result } = renderHook(() => useShowDiscovery())

    await act(() => result.current.find())
    expect(result.current.suggestions).toEqual(suggestions)
    await act(() => result.current.find())

    expect(podcasts.discoverShows).toHaveBeenNthCalledWith(1, [])
    expect(podcasts.discoverShows).toHaveBeenNthCalledWith(2, suggestions.map((show) => show.title))
    expect(result.current.suggestions).toEqual(others)
  })

  it('keeps the server’s plain message when no shows came', async () => {
    vi.mocked(podcasts.discoverShows).mockRejectedValue(new Error("Find a new show didn't come up with enough shows this time. Please try again."))
    const { result } = renderHook(() => useShowDiscovery())

    await act(() => result.current.find())

    expect(result.current.error).toBe("Find a new show didn't come up with enough shows this time. Please try again.")
    expect(result.current.isFinding).toBe(false)
  })
})
