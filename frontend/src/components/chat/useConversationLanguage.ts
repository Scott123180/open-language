import { usePracticeLanguages } from '../../hooks/usePracticeLanguages'
import type { Conversation } from '../../services/api'

export interface ConversationLanguage {
  targetCode: string
  targetName: string
  nativeName: string
  /** True while the catalogue loads, so a slow request never blocks audio. */
  isVoiceInstalled: boolean
  voiceUnavailableMessage: string | null
}

/** A conversation's own language — never the current setting — and whether it can be spoken. */
export function useConversationLanguage(conversation: Conversation | null): ConversationLanguage {
  const { languages } = usePracticeLanguages()
  const targetCode = conversation?.target_language ?? ''
  const entry = languages.find((language) => language.language_id === targetCode)
  return {
    targetCode,
    targetName: conversation?.target_language_name ?? '',
    nativeName: conversation?.native_language_name ?? '',
    isVoiceInstalled: entry?.is_voice_installed ?? true,
    voiceUnavailableMessage: entry?.voice_unavailable_message ?? null,
  }
}
