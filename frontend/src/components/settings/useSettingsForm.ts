import { useEffect, useState } from 'react'
import type { Dispatch, SetStateAction } from 'react'
import { usePracticeLanguages } from '../../hooks/usePracticeLanguages'
import * as api from '../../services/api'
import type {
  ConversationLevelId,
  CorrectionMode,
  PracticeLanguageOption,
  VoiceOption,
} from '../../services/api'
import type { LlmSelectionValue } from './LlmProviderFields'

export interface SettingsValues {
  llm: LlmSelectionValue
  practiceLanguage: string
  whisperModel: string
  ttsVoice: string
  suggestionCount: number
  correctionMode: CorrectionMode
  conversationLevel: ConversationLevelId
}

interface SaveStatus {
  isSaving: boolean
  successMessage: string | null
  errorMessage: string | null
}

type Setter<T> = (value: T) => void

export interface SettingsForm extends SettingsValues, SaveStatus {
  isLoading: boolean
  voices: VoiceOption[]
  practiceLanguages: PracticeLanguageOption[]
  // The voices that speak the form's practice language (FR-015).
  voicesForLanguage: VoiceOption[]
  setLlm: Setter<LlmSelectionValue>
  setPracticeLanguage: Setter<string>
  setWhisperModel: Setter<string>
  setTtsVoice: Setter<string>
  setSuggestionCount: Setter<number>
  setCorrectionMode: Setter<CorrectionMode>
  setConversationLevel: Setter<ConversationLevelId>
  save: () => Promise<void>
}

// Replaced by the saved choice on load; an unloaded choice is never sent.
const UNLOADED_LLM: LlmSelectionValue = { provider: '', model: '', effort: '' }
const INITIAL_VALUES: SettingsValues = {
  llm: UNLOADED_LLM,
  practiceLanguage: '',
  whisperModel: 'base',
  ttsVoice: '',
  suggestionCount: 3,
  correctionMode: 'off',
  conversationLevel: 'natural',
}
const IDLE: SaveStatus = { isSaving: false, successMessage: null, errorMessage: null }
const SAVED_MESSAGE = 'Settings saved.'
const SAVE_FAILED_MESSAGE = 'Failed to save settings'

/** The Settings screen's form: stored values, their setters, and one Save for all of them. */
export function useSettingsForm(): SettingsForm {
  const [values, setValues] = useState<SettingsValues>(INITIAL_VALUES)
  const isLoading = useStoredSettings(setValues)
  const voices = useVoices()
  const { languages } = usePracticeLanguages()
  const { status, save } = useSave(values)
  const voicesForLanguage = voices.filter((voice) => voice.language === values.practiceLanguage)
  const setPracticeLanguage = practiceLanguageSetter(setValues, languages)
  return {
    ...{ ...values, ...status, isLoading, voices, voicesForLanguage, save },
    ...{ practiceLanguages: languages, setPracticeLanguage, ...valueSetters(setValues) },
  }
}

/** Choosing a language also chooses that language's remembered voice. */
function practiceLanguageSetter(
  setValues: Dispatch<SetStateAction<SettingsValues>>,
  languages: PracticeLanguageOption[],
): Setter<string> {
  return (languageId) =>
    setValues((current) => ({
      ...current,
      practiceLanguage: languageId,
      ttsVoice:
        languages.find((language) => language.language_id === languageId)?.selected_voice ??
        current.ttsVoice,
    }))
}

function valueSetters(setValues: Dispatch<SetStateAction<SettingsValues>>) {
  const setter =
    <K extends keyof SettingsValues>(key: K) =>
    (value: SettingsValues[K]) =>
      setValues((current) => ({ ...current, [key]: value }))
  return {
    setLlm: setter('llm'),
    setWhisperModel: setter('whisperModel'),
    setTtsVoice: setter('ttsVoice'),
    setSuggestionCount: setter('suggestionCount'),
    setCorrectionMode: setter('correctionMode'),
    setConversationLevel: setter('conversationLevel'),
  }
}

function useStoredSettings(onLoad: Setter<SettingsValues>): boolean {
  const [isLoading, setIsLoading] = useState(true)
  useEffect(() => {
    api
      .getSettings()
      .then((settings) => onLoad(toValues(settings)))
      .catch(() => {})
      .finally(() => setIsLoading(false))
  }, [onLoad])
  return isLoading
}

function useVoices(): VoiceOption[] {
  const [voices, setVoices] = useState<VoiceOption[]>([])
  useEffect(() => {
    api
      .getVoices()
      .then(setVoices)
      .catch(() => {})
  }, [])
  return voices
}

function useSave(values: SettingsValues) {
  const [status, setStatus] = useState<SaveStatus>(IDLE)
  const save = async () => {
    setStatus({ ...IDLE, isSaving: true })
    try {
      await api.updateSettings(toUpdate(values))
      setStatus({ ...IDLE, successMessage: SAVED_MESSAGE })
    } catch (e) {
      setStatus({ ...IDLE, errorMessage: e instanceof Error ? e.message : SAVE_FAILED_MESSAGE })
    }
  }
  return { status, save }
}

function toValues(settings: api.AppSettings): SettingsValues {
  return {
    llm: {
      provider: settings.llm_provider,
      model: settings.llm_model,
      effort: settings.llm_effort,
    },
    practiceLanguage: settings.target_language,
    whisperModel: settings.whisper_model,
    ttsVoice: settings.tts_voice,
    suggestionCount: settings.suggestion_count,
    correctionMode: settings.correction_mode,
    conversationLevel: settings.conversation_level,
  }
}

function toUpdate({ llm, ...values }: SettingsValues): Partial<api.AppSettings> {
  return {
    ...(llm.provider && {
      llm_provider: llm.provider,
      llm_model: llm.model,
      llm_effort: llm.effort,
    }),
    ...(values.practiceLanguage && { target_language: values.practiceLanguage }),
    whisper_model: values.whisperModel,
    tts_voice: values.ttsVoice,
    suggestion_count: values.suggestionCount,
    correction_mode: values.correctionMode,
    conversation_level: values.conversationLevel,
  }
}
