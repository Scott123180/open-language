import { renderHook, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as api from '../../services/api'
import { useConversationLanguage } from './useConversationLanguage'

vi.mock('../../services/api')

const GERMAN_MISSING = "The German voice isn't installed."

const languages: api.PracticeLanguageOption[] = [
  {
    language_id: 'es',
    display_name: 'Spanish',
    is_default: true,
    default_voice: 'es_ES-davefx-medium',
    selected_voice: 'es_ES-davefx-medium',
    is_voice_installed: true,
    voice_unavailable_message: null,
  },
  {
    language_id: 'de',
    display_name: 'German',
    is_default: false,
    default_voice: 'de_DE-thorsten-medium',
    selected_voice: 'de_DE-thorsten-medium',
    is_voice_installed: false,
    voice_unavailable_message: GERMAN_MISSING,
  },
]

const conversationIn = (code: string, name: string) =>
  ({
    target_language: code,
    native_language: 'en',
    target_language_name: name,
    native_language_name: 'English',
  }) as api.Conversation

describe('useConversationLanguage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.getPracticeLanguages).mockResolvedValue(languages)
    vi.mocked(api.getSettings).mockResolvedValue({ target_language: 'es' } as api.AppSettings)
  })

  it('takes the codes and names from the conversation, not the setting', () => {
    const { result } = renderHook(() => useConversationLanguage(conversationIn('de', 'German')))

    expect(result.current).toMatchObject({
      targetCode: 'de',
      targetName: 'German',
      nativeName: 'English',
    })
  })

  it('reports whether the conversation language can be spoken', async () => {
    const { result } = renderHook(() => useConversationLanguage(conversationIn('de', 'German')))

    await waitFor(() => expect(result.current.isVoiceInstalled).toBe(false))
    expect(result.current.voiceUnavailableMessage).toBe(GERMAN_MISSING)
  })

  it('reports an installed voice with no message', async () => {
    const { result } = renderHook(() => useConversationLanguage(conversationIn('es', 'Spanish')))

    await waitFor(() => expect(api.getPracticeLanguages).toHaveBeenCalled())
    expect(result.current.isVoiceInstalled).toBe(true)
    expect(result.current.voiceUnavailableMessage).toBeNull()
  })

  it('treats the voice as installed while the catalogue is loading', () => {
    vi.mocked(api.getPracticeLanguages).mockReturnValue(new Promise(() => {}))

    const { result } = renderHook(() => useConversationLanguage(conversationIn('de', 'German')))

    expect(result.current.isVoiceInstalled).toBe(true)
    expect(result.current.voiceUnavailableMessage).toBeNull()
  })

  it('is empty until the conversation has loaded', () => {
    const { result } = renderHook(() => useConversationLanguage(null))

    expect(result.current).toMatchObject({ targetCode: '', targetName: '', nativeName: '' })
  })
})
