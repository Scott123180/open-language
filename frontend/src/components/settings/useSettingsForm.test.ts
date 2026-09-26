import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as api from '../../services/api'
import { useSettingsForm } from './useSettingsForm'

vi.mock('../../services/api')

const storedSettings: api.AppSettings = {
  llm_provider: 'ollama',
  llm_model: 'llama3.1:8b',
  llm_effort: 'low',
  target_language: 'es',
  native_language: 'en',
  tts_voice: 'es_ES-mls-medium',
  suggestion_count: 2,
  whisper_model: 'small',
  correction_mode: 'gentle',
  conversation_level: 'natural',
  updated_at: '2026-09-26T10:00:00Z',
}

const voices: api.VoiceOption[] = [
  {
    key: 'es_ES-mls-medium',
    display_name: 'Marta (Spain)',
    gender: 'female',
    locale: 'es_ES',
    quality: 'medium',
    speaking_rate: 'natural',
  },
]

async function renderLoadedForm() {
  const hook = renderHook(() => useSettingsForm())
  await waitFor(() => expect(hook.result.current.isLoading).toBe(false))
  return hook
}

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(api.getSettings).mockResolvedValue(storedSettings)
  vi.mocked(api.getVoices).mockResolvedValue(voices)
})

describe('useSettingsForm — loading', () => {
  it('is loading until the stored settings arrive', () => {
    vi.mocked(api.getSettings).mockReturnValue(new Promise(() => {}))

    const { result } = renderHook(() => useSettingsForm())

    expect(result.current.isLoading).toBe(true)
  })

  it('loads each stored field and clears isLoading', async () => {
    const { result } = await renderLoadedForm()

    expect(result.current.llm).toEqual({ provider: 'ollama', model: 'llama3.1:8b', effort: 'low' })
    expect(result.current.whisperModel).toBe('small')
    expect(result.current.ttsVoice).toBe('es_ES-mls-medium')
    expect(result.current.suggestionCount).toBe(2)
    expect(result.current.correctionMode).toBe('gentle')
    expect(result.current.conversationLevel).toBe('natural')
  })

  it('loads a stored conversation level', async () => {
    vi.mocked(api.getSettings).mockResolvedValue({
      ...storedSettings,
      conversation_level: 'beginner',
    })

    const { result } = await renderLoadedForm()

    expect(result.current.conversationLevel).toBe('beginner')
  })

  it('loads the voice list', async () => {
    const { result } = await renderLoadedForm()

    await waitFor(() => expect(result.current.voices).toEqual(voices))
  })

  it('clears isLoading when the settings fail to load', async () => {
    vi.mocked(api.getSettings).mockRejectedValue(new Error('offline'))

    const { result } = renderHook(() => useSettingsForm())

    await waitFor(() => expect(result.current.isLoading).toBe(false))
  })
})

describe('useSettingsForm — editing', () => {
  it('exposes a setter for each field', async () => {
    const { result } = await renderLoadedForm()

    act(() => {
      result.current.setLlm({ provider: 'claude', model: 'sonnet', effort: 'high' })
      result.current.setWhisperModel('medium')
      result.current.setTtsVoice('es_MX-claude-high')
      result.current.setSuggestionCount(5)
      result.current.setCorrectionMode('strict')
      result.current.setConversationLevel('intermediate')
    })

    expect(result.current.llm).toEqual({ provider: 'claude', model: 'sonnet', effort: 'high' })
    expect(result.current.whisperModel).toBe('medium')
    expect(result.current.ttsVoice).toBe('es_MX-claude-high')
    expect(result.current.suggestionCount).toBe(5)
    expect(result.current.correctionMode).toBe('strict')
    expect(result.current.conversationLevel).toBe('intermediate')
  })
})

describe('useSettingsForm — saving', () => {
  it('sends every field in one updateSettings call', async () => {
    vi.mocked(api.updateSettings).mockResolvedValue(storedSettings)
    const { result } = await renderLoadedForm()

    await act(() => result.current.save())

    expect(api.updateSettings).toHaveBeenCalledTimes(1)
    expect(api.updateSettings).toHaveBeenCalledWith({
      llm_provider: 'ollama',
      llm_model: 'llama3.1:8b',
      llm_effort: 'low',
      whisper_model: 'small',
      tts_voice: 'es_ES-mls-medium',
      suggestion_count: 2,
      correction_mode: 'gentle',
      conversation_level: 'natural',
    })
  })

  it('never sends an LLM selection that did not load', async () => {
    vi.mocked(api.getSettings).mockRejectedValue(new Error('offline'))
    vi.mocked(api.updateSettings).mockResolvedValue(storedSettings)
    const { result } = await renderLoadedForm()

    await act(() => result.current.save())

    expect(vi.mocked(api.updateSettings).mock.calls[0][0]).not.toHaveProperty('llm_provider')
  })

  it('is saving while the request is pending, then shows the success message', async () => {
    let finish: (value: api.AppSettings) => void = () => {}
    vi.mocked(api.updateSettings).mockReturnValue(new Promise((resolve) => (finish = resolve)))
    const { result } = await renderLoadedForm()

    act(() => void result.current.save())
    expect(result.current.isSaving).toBe(true)

    await act(async () => finish(storedSettings))
    expect(result.current.isSaving).toBe(false)
    expect(result.current.successMessage).toBe('Settings saved.')
    expect(result.current.errorMessage).toBeNull()
  })

  it('a failed save shows the error message', async () => {
    vi.mocked(api.updateSettings).mockRejectedValue(new Error('Server error'))
    const { result } = await renderLoadedForm()

    await act(() => result.current.save())

    expect(result.current.errorMessage).toBe('Server error')
    expect(result.current.successMessage).toBeNull()
    expect(result.current.isSaving).toBe(false)
  })
})
