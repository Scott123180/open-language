import { renderHook, waitFor, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as api from '../services/api'
import { useConversationSummary } from './useConversationSummary'

vi.mock('../services/api')

const ready: api.ConversationSummary = {
  status: 'ready',
  conversation_id: 57,
  up_to_message_id: 9,
  conversation_language: 'de',
  conversation_language_name: 'German',
  native_language_name: 'English',
  points: [{ conversation_language: 'Lena mag Märkte.', english: 'Lena likes markets.' }],
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('useConversationSummary', () => {
  it('fetches nothing while closed', () => {
    renderHook(() => useConversationSummary(57, false))

    expect(api.getConversationSummary).not.toHaveBeenCalled()
  })

  it('fetches when opened', async () => {
    vi.mocked(api.getConversationSummary).mockResolvedValue(ready)

    const { result } = renderHook(() => useConversationSummary(57, true))

    await waitFor(() => expect(result.current.summary).toEqual(ready))
    expect(api.getConversationSummary).toHaveBeenCalledWith(57)
  })

  it('fetches again when a new line has been added', async () => {
    vi.mocked(api.getConversationSummary).mockResolvedValue(ready)
    const { rerender } = renderHook(({ last }) => useConversationSummary(57, true, last), { initialProps: { last: 8 } })
    await waitFor(() => expect(api.getConversationSummary).toHaveBeenCalledTimes(1))

    rerender({ last: 9 })

    await waitFor(() => expect(api.getConversationSummary).toHaveBeenCalledTimes(2))
  })

  it('exposes the too-early answer', async () => {
    vi.mocked(api.getConversationSummary).mockResolvedValue({ status: 'too_early', message: 'Nothing yet.' })

    const { result } = renderHook(() => useConversationSummary(57, true))

    await waitFor(() => expect(result.current.summary?.status).toBe('too_early'))
  })

  it('exposes a failure and retries', async () => {
    vi.mocked(api.getConversationSummary)
      .mockRejectedValueOnce(new Error('The AI is not responding.'))
      .mockResolvedValueOnce(ready)
    const { result } = renderHook(() => useConversationSummary(57, true))
    await waitFor(() => expect(result.current.error).toBe('The AI is not responding.'))

    act(() => result.current.retry())

    await waitFor(() => expect(result.current.summary).toEqual(ready))
    expect(result.current.error).toBeNull()
  })
})
