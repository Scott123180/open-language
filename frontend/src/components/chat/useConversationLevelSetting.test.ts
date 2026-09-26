import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as api from '../../services/api'
import { useConversationLevelSetting } from './useConversationLevelSetting'

vi.mock('../../services/api')

const levels: api.ConversationLevelOption[] = [
  {
    level_id: 'beginner',
    label: 'Beginner',
    cefr_label: 'A1',
    description: 'Very short, simple sentences — like talking with a young child.',
  },
  {
    level_id: 'intermediate',
    label: 'Intermediate',
    cefr_label: 'B1',
    description: 'Connected, everyday speech from a clear, considerate adult — no rare words.',
  },
]

const stored = { conversation_level: 'intermediate' } as api.AppSettings

async function renderLoaded() {
  const hook = renderHook(() => useConversationLevelSetting())
  await waitFor(() => expect(hook.result.current.level).toBe('intermediate'))
  await waitFor(() => expect(hook.result.current.levels).toEqual(levels))
  return hook
}

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(api.getSettings).mockResolvedValue(stored)
  vi.mocked(api.getConversationLevels).mockResolvedValue(levels)
})

describe('useConversationLevelSetting — loading', () => {
  it('has no level until the stored settings arrive', () => {
    vi.mocked(api.getSettings).mockReturnValue(new Promise(() => {}))

    const { result } = renderHook(() => useConversationLevelSetting())

    expect(result.current.level).toBeNull()
  })

  it('loads the stored level and the catalogue on mount', async () => {
    const { result } = await renderLoaded()

    expect(result.current).toMatchObject({ isSaving: false, announcement: null, error: null })
  })

  it('explains what to do when the stored level cannot be loaded', async () => {
    vi.mocked(api.getSettings).mockRejectedValue(new Error('offline'))

    const { result } = renderHook(() => useConversationLevelSetting())

    await waitFor(() => expect(result.current.error).toMatch(/could not be loaded.*reload/i))
    expect(result.current.level).toBeNull()
  })

  it('explains what to do when the level list cannot be loaded', async () => {
    vi.mocked(api.getConversationLevels).mockRejectedValue(new Error('offline'))

    const { result } = renderHook(() => useConversationLevelSetting())

    await waitFor(() => expect(result.current.error).toMatch(/could not be loaded.*reload/i))
    expect(result.current.levels).toEqual([])
  })
})

describe('useConversationLevelSetting — changing the level', () => {
  it('shows the new level immediately, before the save resolves', async () => {
    vi.mocked(api.updateSettings).mockReturnValue(new Promise(() => {}))
    const { result } = await renderLoaded()

    act(() => void result.current.changeLevel('beginner'))

    expect(result.current.level).toBe('beginner')
    expect(result.current.isSaving).toBe(true)
  })

  it('saves only the level', async () => {
    vi.mocked(api.updateSettings).mockResolvedValue(stored)
    const { result } = await renderLoaded()

    await act(() => result.current.changeLevel('beginner'))

    expect(api.updateSettings).toHaveBeenCalledTimes(1)
    expect(api.updateSettings).toHaveBeenCalledWith({ conversation_level: 'beginner' })
  })

  it('announces when the change applies once the save succeeds', async () => {
    vi.mocked(api.updateSettings).mockResolvedValue(stored)
    const { result } = await renderLoaded()

    await act(() => result.current.changeLevel('beginner'))

    expect(result.current.isSaving).toBe(false)
    expect(result.current.announcement).toBe(
      'Level set to Beginner. It applies from the next reply.'
    )
    expect(result.current.error).toBeNull()
  })

  it('reverts to the previous level and explains when the save fails', async () => {
    vi.mocked(api.updateSettings).mockRejectedValue(new Error('HTTP 500'))
    const { result } = await renderLoaded()

    await act(() => result.current.changeLevel('beginner'))

    expect(result.current.level).toBe('intermediate')
    expect(result.current.isSaving).toBe(false)
    expect(result.current.announcement).toBeNull()
    expect(result.current.error).toMatch(/level was not changed/i)
    expect(result.current.error).toMatch(/try again/i)
  })

  it('clears an earlier announcement when a later save fails', async () => {
    vi.mocked(api.updateSettings).mockResolvedValueOnce(stored)
    vi.mocked(api.updateSettings).mockRejectedValueOnce(new Error('HTTP 500'))
    const { result } = await renderLoaded()

    await act(() => result.current.changeLevel('beginner'))
    await act(() => result.current.changeLevel('intermediate'))

    expect(result.current.announcement).toBeNull()
    expect(result.current.level).toBe('beginner')
  })
})
