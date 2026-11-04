import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as podcasts from '../../services/podcastsApi'
import { useSubjectSuggestions } from './useSubjectSuggestions'

vi.mock('../../services/podcastsApi')

const show = { title: 'Big Little Questions', premise: 'Everyday curiosities.', topic: 'everyday curiosities' }

beforeEach(() => {
  vi.clearAllMocks()
})

describe('useSubjectSuggestions (011 FR-010a)', () => {
  it('asks for the show, then for the series, with nothing to avoid at first', async () => {
    vi.mocked(podcasts.suggestSubjects).mockResolvedValue({ subjects: ['why cats purr'] })
    const { result } = renderHook(() => useSubjectSuggestions(show, 4))

    act(() => result.current.ask())

    await waitFor(() => expect(result.current.phase).toBe('shown'))
    expect(podcasts.suggestSubjects).toHaveBeenCalledWith(show, 4, [])
    expect(result.current.subjects).toEqual(['why cats purr'])
  })

  it('avoids every subject shown so far, at most ten', async () => {
    const twelve = Array.from({ length: 12 }, (_, n) => `s${n}`)
    vi.mocked(podcasts.suggestSubjects).mockResolvedValueOnce({ subjects: twelve }).mockResolvedValue({ subjects: [] })
    const { result } = renderHook(() => useSubjectSuggestions(show, null))
    act(() => result.current.ask())
    await waitFor(() => expect(result.current.phase).toBe('shown'))

    act(() => result.current.ask())

    await waitFor(() => expect(result.current.phase).toBe('empty'))
    expect(podcasts.suggestSubjects).toHaveBeenLastCalledWith(show, null, twelve.slice(-10))
  })

  it('shows the provider’s message when it fails', async () => {
    vi.mocked(podcasts.suggestSubjects).mockRejectedValue(new Error("Ollama isn't running."))
    const { result } = renderHook(() => useSubjectSuggestions(show, null))

    act(() => result.current.ask())

    await waitFor(() => expect(result.current.phase).toBe('error'))
    expect(result.current.message).toBe("Ollama isn't running.")
  })
})
