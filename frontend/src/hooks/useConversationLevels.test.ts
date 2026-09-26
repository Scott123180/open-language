import { renderHook, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as api from '../services/api'
import { useConversationLevels } from './useConversationLevels'

vi.mock('../services/api')

const levels: api.ConversationLevelOption[] = [
  {
    level_id: 'beginner',
    label: 'Beginner',
    cefr_label: 'A1',
    description: 'Very short, simple sentences — like talking with a young child.',
  },
  {
    level_id: 'natural',
    label: 'Natural',
    cefr_label: 'No limit',
    description: 'Ordinary everyday native speech, with no limits.',
  },
]

describe('useConversationLevels', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('starts loading with no levels', () => {
    vi.mocked(api.getConversationLevels).mockReturnValue(new Promise(() => {}))

    const { result } = renderHook(() => useConversationLevels())

    expect(result.current).toEqual({ levels: [], isLoading: true, error: null })
  })

  it('loads the level list and clears isLoading', async () => {
    vi.mocked(api.getConversationLevels).mockResolvedValue(levels)

    const { result } = renderHook(() => useConversationLevels())

    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.levels).toEqual(levels)
    expect(result.current.error).toBeNull()
  })

  it('a failed load sets an error and leaves the levels empty', async () => {
    vi.mocked(api.getConversationLevels).mockRejectedValue(new Error('HTTP 500'))

    const { result } = renderHook(() => useConversationLevels())

    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.levels).toEqual([])
    expect(result.current.error).toMatch(/levels could not be loaded/i)
  })
})
