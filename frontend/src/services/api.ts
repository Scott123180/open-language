const BASE = '/api'

export interface Scenario {
  id: string
  title: string
  description: string
}

export interface Conversation {
  id: number
  scenario_id: string
  scenario_title: string
  target_language: string
  native_language: string
  target_language_name: string
  native_language_name: string
  status: string
  started_at: string
  ended_at: string | null
  llm_model: string
  custom_prompt: string | null
}

export interface Message {
  id: number
  conversation_id: number
  role: 'user' | 'assistant'
  content: string
  input_source: 'voice' | 'keyboard' | null
  created_at: string
  tts_audio_path: string | null
}

export interface LearningToolResult {
  result: string
  cached: boolean
}

export interface VocabularyItem {
  id: number
  word: string
  translation: string
  target_language: string
  native_language: string
  source_conversation_id: number | null
  saved_at: string
}

export interface AppSettings {
  llm_provider: string
  llm_model: string
  llm_effort: string
  target_language: string
  native_language: string
  tts_voice: string
  suggestion_count: number
  whisper_model: string
  correction_mode: CorrectionMode
  conversation_level: ConversationLevelId
  updated_at: string
}

export type CorrectionMode = 'off' | 'gentle' | 'strict'

export type ConversationLevelId = 'beginner' | 'elementary' | 'intermediate' | 'natural'

/** One conversation level as the learner sees it (005 contracts/api.md §1). */
export interface ConversationLevelOption {
  level_id: ConversationLevelId
  label: string
  cefr_label: string
  description: string
}

export interface ModelOption {
  model_id: string
  label: string
}

export interface EffortOption {
  effort_id: string
  label: string
}

export type ProviderUnavailableReason = 'not_installed' | 'not_signed_in' | 'not_on_plan'

/** One catalogue provider and whether it can be used right now (contracts/api.md §1.1). */
export interface LlmProviderOption {
  provider_id: string
  display_name: string
  is_local: boolean
  models: ModelOption[]
  default_model: string
  effort_levels: EffortOption[]
  default_effort: string | null
  // What leaves the machine when this provider is selected; null for a local provider.
  privacy_notice: string | null
  is_available: boolean
  unavailable_reason: ProviderUnavailableReason | null
  unavailable_message: string | null
}

export type FeedbackKind = 'correction' | 'repeat_request'

export interface FeedbackNoteData {
  id: number
  message_id: number
  kind: FeedbackKind
  category: string | null
  error_fragment: string | null
  corrected_text: string | null
  explanation: string
  mode: 'gentle' | 'strict'
  rank: number
  created_at: string
}

export interface ConversationFeedback {
  conversation_id: number
  awaiting_retry: boolean
  awaiting_clarification: boolean
  consecutive_corrected_attempts: number
  feedback: FeedbackNoteData[]
}

export interface VoiceOption {
  key: string
  display_name: string
  gender: string
  locale: string
  quality: string
  speaking_rate: string
  language: string
  is_installed: boolean
}

/** One practice language, the learner's voice for it, and whether that voice can speak. */
export interface PracticeLanguageOption {
  language_id: string
  display_name: string
  is_default: boolean
  default_voice: string
  selected_voice: string
  is_voice_installed: boolean
  voice_unavailable_message: string | null
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

export const getCurrentScenario = (): Promise<Scenario> =>
  apiFetch('/scenarios/current')

export const getNextScenario = (excludeId?: string): Promise<Scenario> => {
  const qs = excludeId ? `?exclude_id=${encodeURIComponent(excludeId)}` : ''
  return apiFetch(`/scenarios/next${qs}`)
}

export const createConversation = (scenarioId: string | null, customPrompt?: string): Promise<Conversation> =>
  apiFetch('/conversations', {
    method: 'POST',
    body: JSON.stringify(
      customPrompt ? { custom_prompt: customPrompt } : { scenario_id: scenarioId },
    ),
  })

export const getConversations = (): Promise<Conversation[]> =>
  apiFetch('/conversations')

export const getConversation = (conversationId: number): Promise<Conversation> =>
  apiFetch(`/conversations/${conversationId}`)

export const getMessages = (conversationId: number): Promise<Message[]> =>
  apiFetch(`/conversations/${conversationId}/messages`)

export const completeConversation = (conversationId: number): Promise<Conversation> =>
  apiFetch(`/conversations/${conversationId}`, {
    method: 'PATCH',
    body: JSON.stringify({ status: 'completed' }),
  })

export interface TranscriptionResult {
  text: string
  detected_language: string | null
  confidence: number | null
  is_low_confidence: boolean
}

export const transcribeAudio = async (blob: Blob, language?: string): Promise<TranscriptionResult> => {
  const form = new FormData()
  form.append('file', blob, 'audio.wav')
  if (language) form.append('language', language)
  const res = await fetch(`${BASE}/audio/transcribe`, { method: 'POST', body: form })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? `HTTP ${res.status}`)
  }
  return res.json()
}

/**
 * Ask the backend to get this conversation's session ready before the next turn (FR-S07).
 * Fire-and-forget: the warm-up is invisible, so every failure is ignored and the first real
 * turn reports any problem with its normal message.
 */
export const warmSession = async (conversationId: number): Promise<void> => {
  try {
    await fetch(`${BASE}/chat/${conversationId}/session`, { method: 'POST' })
  } catch {
    // Deliberately silent: see the doc comment above.
  }
}

export const getTtsUrl = (messageId: number): string =>
  `${BASE}/audio/tts/${messageId}`

async function readSseStream(
  res: Response,
  onToken: (t: string) => void,
  onDone: (data: unknown) => void,
  onError: (e: string) => void,
  onEvent?: (event: string, data: unknown) => void,
): Promise<void> {
  const reader = res.body?.getReader()
  if (!reader) { onError('No response body'); return }
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const raw = line.slice(6).trim()
        if (raw === '[DONE]') continue
        try {
          const parsed = JSON.parse(raw)
          if (parsed.token !== undefined) onToken(parsed.token)
          else if (parsed.done) onDone(parsed)
          else if (parsed.error) onError(parsed.error)
          else if (parsed.event && onEvent) onEvent(parsed.event, parsed)
        } catch { /* ignore malformed */ }
      }
    }
  }
}

export const streamChatOpen = async (
  conversationId: number,
  onToken: (t: string) => void,
  onDone: (data: { message_id: number; full_content: string }) => void,
  onError: (e: string) => void,
): Promise<void> => {
  const res = await fetch(`${BASE}/chat/${conversationId}/open`, { method: 'POST' })
  if (!res.ok) { onError(`HTTP ${res.status}`); return }
  await readSseStream(res, onToken, onDone as (d: unknown) => void, onError)
}

export interface FeedbackEventData {
  message_id: number
  awaiting_retry: boolean
  notes: FeedbackNoteData[]
}

export const streamChatMessage = async (
  conversationId: number,
  content: string,
  inputSource: 'voice' | 'keyboard',
  onUserSaved: (messageId: number) => void,
  onToken: (t: string) => void,
  onDone: (data: { message_id: number | null }) => void,
  onError: (e: string) => void,
  onFeedback?: (data: FeedbackEventData) => void,
  transcriptionConfidence?: number,
): Promise<void> => {
  const body: Record<string, unknown> = { content, input_source: inputSource }
  // 0.0 is a meaningful confidence (hallucination-on-silence), so test for null.
  if (transcriptionConfidence != null) body.transcription_confidence = transcriptionConfidence
  const res = await fetch(`${BASE}/chat/${conversationId}/message`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) { onError(`HTTP ${res.status}`); return }
  await readSseStream(
    res,
    onToken,
    (data) => onDone(data as { message_id: number | null }),
    onError,
    (event, data) => {
      if (event === 'user_message_saved') {
        const d = data as { message_id: number }
        onUserSaved(d.message_id)
      } else if (event === 'feedback') {
        onFeedback?.(data as FeedbackEventData)
      }
    },
  )
}

export const checkGrammar = (messageId: number, content: string, precedingMessage?: string): Promise<LearningToolResult> =>
  apiFetch('/learning/grammar', {
    method: 'POST',
    body: JSON.stringify({ message_id: messageId, content, preceding_message: precedingMessage ?? null }),
  })

// The server takes each learning aid's languages from the message's conversation (FR-009).
export const translateMessage = (messageId: number, content: string): Promise<LearningToolResult> =>
  apiFetch('/learning/translate', {
    method: 'POST',
    body: JSON.stringify({ message_id: messageId, content }),
  })

export const getAlternativePhrasing = (
  messageId: number,
  content: string,
): Promise<LearningToolResult> =>
  apiFetch('/learning/phrasing', {
    method: 'POST',
    body: JSON.stringify({ message_id: messageId, content }),
  })

export const lookupWord = (
  messageId: number,
  selection: string,
  sentenceContext?: string,
): Promise<LearningToolResult> =>
  apiFetch('/learning/word-lookup', {
    method: 'POST',
    body: JSON.stringify({
      message_id: messageId,
      selection,
      sentence_context: sentenceContext ?? null,
    }),
  })

export const saveVocabularyItem = (
  word: string,
  translation: string,
  sourceConversationId?: number,
): Promise<VocabularyItem> =>
  apiFetch('/vocabulary', {
    method: 'POST',
    body: JSON.stringify({ word, translation, source_conversation_id: sourceConversationId ?? null }),
  })

export const getVocabulary = (): Promise<VocabularyItem[]> =>
  apiFetch('/vocabulary')

export const getSuggestions = (conversationId: number): Promise<{ suggestions: string[] }> =>
  apiFetch(`/chat/${conversationId}/suggestions`, { method: 'POST' })

export const streamHelper = async (
  content: string,
  helperSessionId: string,
  conversationId: number,
  onToken: (t: string) => void,
  onDone: () => void,
  onError: (e: string) => void,
): Promise<void> => {
  const res = await fetch(`${BASE}/chat/helper`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: content,
      helper_session_id: helperSessionId,
      conversation_id: conversationId,
    }),
  })
  if (!res.ok) { onError(`HTTP ${res.status}`); return }
  await readSseStream(res, onToken, () => onDone(), onError)
}

export const getSettings = (): Promise<AppSettings> =>
  apiFetch('/settings')

export const getConversationLevels = (): Promise<ConversationLevelOption[]> =>
  apiFetch('/settings/conversation-levels')

export const getPracticeLanguages = (): Promise<PracticeLanguageOption[]> =>
  apiFetch('/settings/practice-languages')

export const updateSettings = (updates: Partial<AppSettings>): Promise<AppSettings> =>
  apiFetch('/settings', { method: 'PUT', body: JSON.stringify(updates) })

export const getLlmProviders = (): Promise<LlmProviderOption[]> =>
  apiFetch('/settings/llm-providers')

export const getVoices = (): Promise<VoiceOption[]> =>
  apiFetch('/settings/voices')

export const getConversationFeedback = (conversationId: number): Promise<ConversationFeedback> =>
  apiFetch(`/corrections/conversations/${conversationId}`)
