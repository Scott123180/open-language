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
  target_language: 'Spanish',
  native_language: 'English',
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
  target_language: 'Spanish',
  native_language: 'English',
  tts_voice: 'es_ES-davefx-medium',
  suggestion_count: 3,
  whisper_model: 'base',
  correction_mode: 'off',
  updated_at: '2026-03-20T10:00:00Z',
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
  is_available: true,
  unavailable_reason: null as string | null,
  unavailable_message: null as string | null,
}

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
  { key: 'es_ES-davefx-medium', display_name: 'David (Spain)', gender: 'male', locale: 'es_ES', quality: 'medium', speaking_rate: 'natural' },
  { key: 'es_AR-daniela-high', display_name: 'Daniela (Argentina)', gender: 'female', locale: 'es_AR', quality: 'high', speaking_rate: 'fast' },
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
}

/** Set up all common API mocks needed for the chat page. */
export async function mockChatApis(
  page: Page,
  options: {
    openTokens?: string[]
    openMessageId?: number
    openFullContent?: string
  } = {},
) {
  const {
    openTokens = ['¡Hola', '! ¿Cómo', ' estás?'],
    openMessageId = 1,
    openFullContent = '¡Hola! ¿Cómo estás?',
  } = options

  await page.route('/api/settings', (route) =>
    route.fulfill({ json: mockSettings }),
  )
  await mockLlmProviders(page)
  await page.route('/api/conversations/1', (route) =>
    route.fulfill({ json: mockConversation }),
  )
  await page.route('/api/conversations/1/messages', (route) =>
    route.fulfill({ json: [] }),
  )
  await page.route('/api/corrections/conversations/1', (route) =>
    route.fulfill({ json: emptyConversationFeedback }),
  )
  await page.route('/api/chat/1/open', (route) =>
    route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'text/event-stream' },
      body: makeOpenSseBody(openTokens, openMessageId, openFullContent),
    }),
  )
  await page.route('/api/audio/tts/**', (route) =>
    route.fulfill({ status: 200, body: '' }),
  )
  await mockWarmSession(page)
  await page.route('/api/conversations/1', (route) => {
    if (route.request().method() === 'PATCH') {
      return route.fulfill({ json: { ...mockConversation, status: 'completed' } })
    }
    return route.fulfill({ json: mockConversation })
  })
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
