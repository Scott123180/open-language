import { renderHook, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as api from '../services/api'
import { usePracticeLanguages } from './usePracticeLanguages'

vi.mock('../services/api')

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
    is_voice_installed: true,
    voice_unavailable_message: null,
  },
]

const settingsIn = (target_language: string) =>
  ({ target_language, native_language: 'en' }) as api.AppSettings

describe('usePracticeLanguages', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.getPracticeLanguages).mockResolvedValue(languages)
    vi.mocked(api.getSettings).mockResolvedValue(settingsIn('de'))
  })

  it('starts loading with no languages and no current language', () => {
    vi.mocked(api.getPracticeLanguages).mockReturnValue(new Promise(() => {}))

    const { result } = renderHook(() => usePracticeLanguages())

    expect(result.current.isLoading).toBe(true)
    expect(result.current.languages).toEqual([])
    expect(result.current.current).toBeNull()
  })

  it('loads the catalogue and the practice language', async () => {
    const { result } = renderHook(() => usePracticeLanguages())

    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.languages).toEqual(languages)
    expect(result.current.current?.language_id).toBe('de')
    expect(result.current.error).toBeNull()
  })

  it('names a language by its code', async () => {
    const { result } = renderHook(() => usePracticeLanguages())

    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.nameOf('de')).toBe('German')
  })

  it('shows an unknown code as itself rather than failing', async () => {
    const { result } = renderHook(() => usePracticeLanguages())

    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.nameOf('xx')).toBe('xx')
  })

  it('a failed load sets an error and leaves the languages empty', async () => {
    vi.mocked(api.getPracticeLanguages).mockRejectedValue(new Error('HTTP 500'))

    const { result } = renderHook(() => usePracticeLanguages())

    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.languages).toEqual([])
    expect(result.current.current).toBeNull()
    expect(result.current.error).toMatch(/practice languages could not be loaded/i)
  })
})
