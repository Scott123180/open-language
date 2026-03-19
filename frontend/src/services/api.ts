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
  status: string
  started_at: string
  ended_at: string | null
  llm_model: string
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
  llm_model: string
  target_language: string
  native_language: string
  tts_voice: string
  suggestion_count: number
  updated_at: string
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

export const createConversation = (scenarioId: string): Promise<Conversation> =>
  apiFetch('/conversations', { method: 'POST', body: JSON.stringify({ scenario_id: scenarioId }) })

export const getConversations = (): Promise<Conversation[]> =>
  apiFetch('/conversations')

export const getMessages = (conversationId: number): Promise<Message[]> =>
  apiFetch(`/conversations/${conversationId}/messages`)

export const completeConversation = (conversationId: number): Promise<Conversation> =>
  apiFetch(`/conversations/${conversationId}`, {
    method: 'PATCH',
    body: JSON.stringify({ status: 'completed' }),
  })

export const transcribeAudio = async (blob: Blob): Promise<{ text: string; detected_language: string | null }> => {
  const form = new FormData()
  form.append('file', blob, 'audio.wav')
  const res = await fetch(`${BASE}/audio/transcribe`, { method: 'POST', body: form })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? `HTTP ${res.status}`)
  }
  return res.json()
}

export const getTtsUrl = (messageId: number): string =>
  `${BASE}/audio/tts/${messageId}`

async function readSseStream(
  res: Response,
  onToken: (t: string) => void,
  onDone: (data: unknown) => void,
  onError: (e: string) => void,
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

export const streamChatMessage = async (
  conversationId: number,
  content: string,
  inputSource: 'voice' | 'keyboard',
  onUserSaved: (messageId: number) => void,
  onToken: (t: string) => void,
  onDone: (data: { message_id: number }) => void,
  onError: (e: string) => void,
): Promise<void> => {
  const res = await fetch(`${BASE}/chat/${conversationId}/message`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content, input_source: inputSource }),
  })
  if (!res.ok) { onError(`HTTP ${res.status}`); return }
  await readSseStream(
    res,
    onToken,
    (data) => {
      const d = data as { message_id?: number; user_message_id?: number }
      if (d.user_message_id) onUserSaved(d.user_message_id)
      onDone(d as { message_id: number })
    },
    onError,
  )
}

export const checkGrammar = (messageId: number): Promise<LearningToolResult> =>
  apiFetch('/learning/grammar', { method: 'POST', body: JSON.stringify({ message_id: messageId }) })

export const translateMessage = (messageId: number): Promise<LearningToolResult> =>
  apiFetch('/learning/translate', { method: 'POST', body: JSON.stringify({ message_id: messageId }) })

export const getAlternativePhrasing = (messageId: number): Promise<LearningToolResult> =>
  apiFetch('/learning/phrasing', { method: 'POST', body: JSON.stringify({ message_id: messageId }) })

export const lookupWord = (messageId: number, selection: string): Promise<LearningToolResult> =>
  apiFetch('/learning/word-lookup', {
    method: 'POST',
    body: JSON.stringify({ message_id: messageId, selection }),
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
  onToken: (t: string) => void,
  onDone: () => void,
  onError: (e: string) => void,
): Promise<void> => {
  const res = await fetch(`${BASE}/chat/helper`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content, helper_session_id: helperSessionId }),
  })
  if (!res.ok) { onError(`HTTP ${res.status}`); return }
  await readSseStream(res, onToken, () => onDone(), onError)
}

export const getSettings = (): Promise<AppSettings> =>
  apiFetch('/settings')

export const updateSettings = (updates: Partial<AppSettings>): Promise<AppSettings> =>
  apiFetch('/settings', { method: 'PUT', body: JSON.stringify(updates) })
