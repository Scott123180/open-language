import { useCallback, useEffect, useState } from 'react'
import * as api from '../services/api'

interface LoadedLanguages {
  languages: api.PracticeLanguageOption[]
  practiceLanguageId: string | null
  isLoading: boolean
  error: string | null
}

export interface PracticeLanguagesState {
  languages: api.PracticeLanguageOption[]
  /** The learner's practice language, or null until it has loaded. */
  current: api.PracticeLanguageOption | null
  /** A language's display name; an unknown code is shown as itself. */
  nameOf: (languageId: string) => string
  isLoading: boolean
  error: string | null
}

const LOAD_ERROR = 'Practice languages could not be loaded. Reload the page to try again.'

async function loadLanguages(): Promise<LoadedLanguages> {
  const [languages, settings] = await Promise.all([api.getPracticeLanguages(), api.getSettings()])
  return { languages, practiceLanguageId: settings.target_language, isLoading: false, error: null }
}

/** The language catalogue and the practice language, shared by Settings, Home and Flashcards. */
export function usePracticeLanguages(): PracticeLanguagesState {
  const state = useLoadedLanguages()
  const nameOf = useCallback(
    (languageId: string) =>
      state.languages.find((l) => l.language_id === languageId)?.display_name ?? languageId,
    [state.languages],
  )
  const current = state.languages.find((l) => l.language_id === state.practiceLanguageId) ?? null
  return { languages: state.languages, current, nameOf, isLoading: state.isLoading, error: state.error }
}

const LOADING: LoadedLanguages = { languages: [], practiceLanguageId: null, isLoading: true, error: null }
const FAILED: LoadedLanguages = { ...LOADING, isLoading: false, error: LOAD_ERROR }

function useLoadedLanguages(): LoadedLanguages {
  const [state, setState] = useState<LoadedLanguages>(LOADING)
  useEffect(() => {
    loadLanguages()
      .then(setState)
      .catch(() => setState(FAILED))
  }, [])
  return state
}
