import type { Page } from '@playwright/test'

// ── Mock data ─────────────────────────────────────────────────────────────────

export const mockScenario = {
  id: 'scenario-1',
  title: 'Coffee Shop',
  description: 'Practice ordering coffee in a busy Spanish cafe.',
}

export const mockScenario2 = {
  id: 'scenario-2',
  title: 'Hotel Check-in',
  description: 'Check into a hotel and ask about amenities.',
}

export const mockConversation = {
  id: 1,
  scenario_id: 'scenario-1',
  scenario_title: 'Coffee Shop',
  target_language: 'es',
  native_language: 'en',
  target_language_name: 'Spanish',
  native_language_name: 'English',
  status: 'active',
  started_at: '2026-03-20T10:00:00Z',
  ended_at: null,
  llm_model: 'llama3.1',
  custom_prompt: null,
}

export const mockConversationCompleted = {
  ...mockConversation,
  id: 2,
  scenario_title: 'Hotel Check-in',
  status: 'completed',
  ended_at: '2026-03-20T10:30:00Z',
}

export const mockSettings = {
  llm_provider: 'ollama',
  llm_model: 'llama3.1',
  llm_effort: 'low',
  target_language: 'es',
  native_language: 'en',
  tts_voice: 'es_ES-davefx-medium',
  suggestion_count: 3,
  whisper_model: 'base',
  correction_mode: 'off',
  conversation_level: 'natural',
  updated_at: '2026-03-20T10:00:00Z',
}

/** The level catalogue as `GET /api/settings/conversation-levels` serves it (005 contract §1). */
export const mockConversationLevels = [
  {
    level_id: 'beginner',
    label: 'Beginner',
    cefr_label: 'A1',
    description: 'Very short, simple sentences — like talking with a young child.',
  },
  {
    level_id: 'elementary',
    label: 'Elementary',
    cefr_label: 'A2',
    description: 'Short, clear sentences with everyday words — like talking with a patient friend.',
  },
  {
    level_id: 'intermediate',
    label: 'Intermediate',
    cefr_label: 'B1',
    description: 'Connected, everyday speech from a clear, considerate adult — no rare words.',
  },
  {
    level_id: 'natural',
    label: 'Natural',
    cefr_label: 'No limit',
    description: 'Ordinary everyday native speech, with no limits.',
  },
]

/** A German conversation, for checks that follow the conversation's language, not the setting. */
export const mockGermanConversation = {
  ...mockConversation,
  id: 3,
  scenario_title: 'Coffee Shop',
  target_language: 'de',
  target_language_name: 'German',
}

export const GERMAN_VOICE_UNAVAILABLE_MESSAGE =
  "The German voice isn't installed, so German can't be read aloud. Run ./run.sh --setup to download it. You can keep practising in text."

const SPANISH_LANGUAGE = {
  language_id: 'es',
  display_name: 'Spanish',
  is_default: true,
  default_voice: 'es_ES-davefx-medium',
  selected_voice: 'es_ES-davefx-medium',
  is_voice_installed: true,
  voice_unavailable_message: null as string | null,
}

const GERMAN_LANGUAGE = {
  language_id: 'de',
  display_name: 'German',
  is_default: false,
  default_voice: 'de_DE-thorsten-medium',
  selected_voice: 'de_DE-thorsten-medium',
  is_voice_installed: true,
  voice_unavailable_message: null as string | null,
}

/** The practice-language catalogue with both voices installed (006 contracts §1). */
export const mockPracticeLanguages = [SPANISH_LANGUAGE, GERMAN_LANGUAGE]

/** The catalogue when the German voice has not been downloaded. */
export const mockPracticeLanguagesGermanVoiceMissing = [
  SPANISH_LANGUAGE,
  {
    ...GERMAN_LANGUAGE,
    is_voice_installed: false,
    voice_unavailable_message: GERMAN_VOICE_UNAVAILABLE_MESSAGE as string | null,
  },
]

export async function mockPracticeLanguagesApi(
  page: Page,
  languages: unknown[] = mockPracticeLanguages,
) {
  await page.route('/api/settings/practice-languages', (route) =>
    route.fulfill({ json: languages }),
  )
}

export async function mockConversationLevelsApi(page: Page) {
  await page.route('/api/settings/conversation-levels', (route) =>
    route.fulfill({ json: mockConversationLevels }),
  )
}

const OLLAMA_PROVIDER = {
  provider_id: 'ollama',
  display_name: 'Ollama (local)',
  is_local: true,
  models: [
    { model_id: 'llama3.1:8b', label: 'llama3.1:8b' },
    { model_id: 'llama3.2', label: 'llama3.2' },
    { model_id: 'mistral', label: 'mistral' },
  ],
  default_model: 'llama3.1:8b',
  effort_levels: [] as { effort_id: string; label: string }[],
  default_effort: null as string | null,
  privacy_notice: null as string | null,
  is_available: true,
  unavailable_reason: null as string | null,
  unavailable_message: null as string | null,
}

const CLAUDE_PRIVACY_NOTICE =
  "Your conversation text is sent to Anthropic under your Claude account and counts toward your Claude plan's usage. Your voice recordings and audio stay on your computer."

const CLAUDE_PROVIDER = {
  provider_id: 'claude',
  display_name: 'Claude (via Claude Code)',
  is_local: false,
  models: [
    { model_id: 'sonnet', label: 'Claude Sonnet' },
    { model_id: 'haiku', label: 'Claude Haiku (fastest)' },
    { model_id: 'opus', label: 'Claude Opus (most capable, uses more of your plan)' },
  ],
  default_model: 'sonnet',
  effort_levels: [
    { effort_id: 'low', label: 'Low — fastest replies' },
    { effort_id: 'medium', label: 'Medium' },
    { effort_id: 'high', label: 'High — deeper, slower replies' },
  ],
  default_effort: 'low' as string | null,
  privacy_notice: CLAUDE_PRIVACY_NOTICE as string | null,
  is_available: true,
  unavailable_reason: null as string | null,
  unavailable_message: null as string | null,
}

/** The provider catalogue with Claude signed in and ready (contracts/api.md §1.1). */
export const mockLlmProvidersAvailable = [OLLAMA_PROVIDER, CLAUDE_PROVIDER]

export type ClaudeUnavailableReason = 'not_installed' | 'not_signed_in' | 'not_on_plan'

export const CLAUDE_UNAVAILABLE_MESSAGES: Record<ClaudeUnavailableReason, string> = {
  not_installed: 'Install Claude Code to use Claude.',
  not_signed_in: 'Sign in to Claude Code (run `claude` in a terminal) to use Claude.',
  not_on_plan:
    'Claude Code is signed in with an API key. Sign in with your Claude plan to use it here.',
}

/** The provider catalogue with Claude unavailable for `reason`. */
export function mockLlmProvidersClaudeUnavailable(reason: ClaudeUnavailableReason) {
  return [
    OLLAMA_PROVIDER,
    {
      ...CLAUDE_PROVIDER,
      is_available: false,
      unavailable_reason: reason,
      unavailable_message: CLAUDE_UNAVAILABLE_MESSAGES[reason],
    },
  ]
}

/** Serve the provider catalogue; defaults to Claude available. */
export async function mockLlmProviders(
  page: Page,
  providers: unknown[] = mockLlmProvidersAvailable,
) {
  await page.route('/api/settings/llm-providers', (route) => route.fulfill({ json: providers }))
}

export const mockFeedbackNote = {
  id: 7,
  message_id: 10,
  kind: 'correction',
  category: 'conjugation',
  error_fragment: 'Yo tener',
  corrected_text: 'Yo tengo veinte años',
  explanation: '"Tener" needs to be conjugated: with "yo" it becomes "tengo".',
  mode: 'strict',
  rank: 0,
  created_at: '2026-03-20T10:04:11Z',
}

export const mockRepeatRequestNote = {
  ...mockFeedbackNote,
  id: 8,
  kind: 'repeat_request',
  category: null,
  error_fragment: null,
  corrected_text: null,
  explanation: "I didn't quite catch that — could you say it again?",
}

export const emptyConversationFeedback = {
  conversation_id: 1,
  awaiting_retry: false,
  awaiting_clarification: false,
  consecutive_corrected_attempts: 0,
  feedback: [],
}

export const mockVoices = [
  { key: 'es_ES-davefx-medium', display_name: 'David (Spain)', gender: 'male', locale: 'es_ES', quality: 'medium', speaking_rate: 'natural', language: 'es', is_installed: true },
  { key: 'es_AR-daniela-high', display_name: 'Daniela (Argentina)', gender: 'female', locale: 'es_AR', quality: 'high', speaking_rate: 'fast', language: 'es', is_installed: true },
  { key: 'de_DE-thorsten-medium', display_name: 'Thorsten (Germany)', gender: 'male', locale: 'de_DE', quality: 'medium', speaking_rate: 'natural', language: 'de', is_installed: true },
  { key: 'de_DE-kerstin-low', display_name: 'Kerstin (Germany)', gender: 'female', locale: 'de_DE', quality: 'low', speaking_rate: 'natural', language: 'de', is_installed: true },
]

export const mockMessages = [
  {
    id: 1,
    conversation_id: 1,
    role: 'assistant',
    content: '¡Hola! ¿En qué puedo ayudarte hoy?',
    input_source: null,
    created_at: '2026-03-20T10:00:00Z',
    tts_audio_path: '/audio/1.mp3',
  },
  {
    id: 2,
    conversation_id: 1,
    role: 'user',
    content: 'Quiero un café con leche, por favor.',
    input_source: 'keyboard',
    created_at: '2026-03-20T10:01:00Z',
    tts_audio_path: null,
  },
]

// ── SSE helpers ───────────────────────────────────────────────────────────────

/** Build a complete SSE body for the chat open stream. */
export function makeOpenSseBody(
  tokens: string[],
  messageId: number,
  fullContent: string,
): string {
  const lines = tokens.map((t) => `data: ${JSON.stringify({ token: t })}\n\n`)
  lines.push(
    `data: ${JSON.stringify({ done: true, message_id: messageId, full_content: fullContent })}\n\n`,
  )
  return lines.join('')
}

/** Build a complete SSE body for the chat message stream. */
export function makeMessageSseBody(
  userMessageId: number,
  tokens: string[],
  assistantMessageId: number,
): string {
  const lines: string[] = []
  lines.push(
    `data: ${JSON.stringify({ event: 'user_message_saved', message_id: userMessageId })}\n\n`,
  )
  for (const t of tokens) {
    lines.push(`data: ${JSON.stringify({ token: t })}\n\n`)
  }
  lines.push(`data: ${JSON.stringify({ done: true, message_id: assistantMessageId })}\n\n`)
  return lines.join('')
}

/** Build an SSE body whose turn is a correction and nothing else (Strict, flagged). */
export function makeCorrectionSseBody(
  userMessageId: number,
  notes: Array<Record<string, unknown>>,
  options: { awaitingRetry?: boolean } = {},
): string {
  const { awaitingRetry = true } = options
  const lines: string[] = []
  lines.push(
    `data: ${JSON.stringify({ event: 'user_message_saved', message_id: userMessageId })}\n\n`,
  )
  lines.push(
    `data: ${JSON.stringify({
      event: 'feedback',
      message_id: userMessageId,
      awaiting_retry: awaitingRetry,
      notes,
    })}\n\n`,
  )
  lines.push(`data: ${JSON.stringify({ done: true, message_id: null })}\n\n`)
  return lines.join('')
}

/** Build an SSE body that carries a feedback frame and then streams a reply. */
export function makeMessageWithFeedbackSseBody(
  userMessageId: number,
  notes: Array<Record<string, unknown>>,
  tokens: string[],
  assistantMessageId: number,
): string {
  const lines: string[] = []
  lines.push(
    `data: ${JSON.stringify({ event: 'user_message_saved', message_id: userMessageId })}\n\n`,
  )
  lines.push(
    `data: ${JSON.stringify({
      event: 'feedback',
      message_id: userMessageId,
      awaiting_retry: false,
      notes,
    })}\n\n`,
  )
  for (const t of tokens) {
    lines.push(`data: ${JSON.stringify({ token: t })}\n\n`)
  }
  lines.push(`data: ${JSON.stringify({ done: true, message_id: assistantMessageId })}\n\n`)
  return lines.join('')
}

/** Build a complete SSE body for the helper stream. */
export function makeHelperSseBody(tokens: string[]): string {
  const lines = tokens.map((t) => `data: ${JSON.stringify({ token: t })}\n\n`)
  lines.push(`data: ${JSON.stringify({ done: true })}\n\n`)
  return lines.join('')
}

// ── Route helpers ─────────────────────────────────────────────────────────────

/** Set up all common API mocks needed for the home page. */
export async function mockHomeApis(page: Page) {
  await page.route('/api/scenarios/current', (route) =>
    route.fulfill({ json: mockScenario }),
  )
  await page.route('/api/scenarios/next**', (route) =>
    route.fulfill({ json: mockScenario2 }),
  )
  await page.route('/api/conversations', (route) => {
    if (route.request().method() === 'POST') {
      return route.fulfill({ json: mockConversation })
    }
    return route.fulfill({ json: [mockConversation, mockConversationCompleted] })
  })
  await mockPracticeLanguagesApi(page)
}

interface ChatApiOptions {
  openTokens?: string[]
  openMessageId?: number
  openFullContent?: string
}

/** Set up all common API mocks needed for the chat page. */
export async function mockChatApis(page: Page, options: ChatApiOptions = {}) {
  const {
    openTokens = ['¡Hola', '! ¿Cómo', ' estás?'],
    openMessageId = 1,
    openFullContent = '¡Hola! ¿Cómo estás?',
  } = options

  await page.route('/api/settings', (route) =>
    route.fulfill({ json: mockSettings }),
  )
  await mockLlmProviders(page)
  await mockConversationLevelsApi(page)
  await mockPracticeLanguagesApi(page)
  await mockConversationRoutes(page)
  await mockOpeningRoutes(page, makeOpenSseBody(openTokens, openMessageId, openFullContent))
  await mockWarmSession(page)
}

/** Conversation 1 with no saved messages or feedback; a PATCH ends it. */
export async function mockConversationRoutes(page: Page) {
  await page.route('/api/conversations/1', (route) => {
    if (route.request().method() === 'PATCH') {
      return route.fulfill({ json: { ...mockConversation, status: 'completed' } })
    }
    return route.fulfill({ json: mockConversation })
  })
  await page.route('/api/conversations/1/messages', (route) =>
    route.fulfill({ json: [] }),
  )
  await page.route('/api/corrections/conversations/1', (route) =>
    route.fulfill({ json: emptyConversationFeedback }),
  )
}

/** Conversation 1's opening stream, and silent audio for every spoken reply. */
export async function mockOpeningRoutes(page: Page, openSseBody: string) {
  await page.route('/api/chat/1/open', (route) =>
    route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'text/event-stream' },
      body: openSseBody,
    }),
  )
  await page.route('/api/audio/tts/**', (route) =>
    route.fulfill({ status: 200, body: '' }),
  )
}

/**
 * Mock the conversation warm-up endpoint and record each request's method.
 * `status` lets a test serve a failure; the chat screen must ignore it either way.
 */
export async function mockWarmSession(
  page: Page,
  options: { conversationId?: number; status?: number } = {},
) {
  const { conversationId = 1, status = 202 } = options
  const calls: string[] = []
  await page.route(`/api/chat/${conversationId}/session`, (route) => {
    calls.push(route.request().method())
    const body = status === 202 ? { status: 'warming' } : { detail: 'Internal error' }
    return route.fulfill({ status, json: body })
  })
  return { calls }
}

/** Replace the browser microphone with a recorder that yields one small clip on stop. */
export async function stubMicrophone(page: Page) {
  await page.addInitScript(() => {
    class FakeRecorder {
      ondataavailable: ((e: { data: Blob }) => void) | null = null
      onstop: (() => void) | null = null
      state = 'inactive'
      start() {
        this.state = 'recording'
      }
      stop() {
        this.state = 'inactive'
        this.ondataavailable?.({ data: new Blob(['x'], { type: 'audio/webm' }) })
        this.onstop?.()
      }
    }
    // @ts-expect-error test double
    window.MediaRecorder = FakeRecorder
    // @ts-expect-error test double
    window.MediaRecorder.isTypeSupported = () => true
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: {
        getUserMedia: async () => ({ getTracks: () => [{ stop() {} }] }),
      },
    })
  })
}

/**
 * The German conversation (`mockGermanConversation`, id 3) with no saved messages, its opening
 * line, and every catalogue it loads. Returns the audio requests made, for voice checks.
 */
export async function mockGermanChatApis(page: Page, languages: unknown[] = mockPracticeLanguages) {
  const id = mockGermanConversation.id
  const ttsRequests: string[] = []
  await page.route('/api/settings', (route) => route.fulfill({ json: mockSettings }))
  await mockLlmProviders(page)
  await mockConversationLevelsApi(page)
  await mockPracticeLanguagesApi(page, languages)
  await page.route(`/api/conversations/${id}`, (route) =>
    route.fulfill({ json: mockGermanConversation }),
  )
  await page.route(`/api/conversations/${id}/messages`, (route) => route.fulfill({ json: [] }))
  await page.route(`/api/corrections/conversations/${id}`, (route) =>
    route.fulfill({ json: { ...emptyConversationFeedback, conversation_id: id } }),
  )
  await page.route(`/api/chat/${id}/open`, (route) =>
    route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'text/event-stream' },
      body: makeOpenSseBody(['Guten', ' Tag!'], 30, 'Guten Tag!'),
    }),
  )
  await page.route('/api/audio/tts/**', (route) => {
    ttsRequests.push(route.request().url())
    return route.fulfill({ status: 200, body: '' })
  })
  await mockWarmSession(page, { conversationId: id })
  return { ttsRequests }
}
