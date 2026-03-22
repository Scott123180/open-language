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
  llm_model: 'llama3.1',
  target_language: 'Spanish',
  native_language: 'English',
  tts_voice: 'es_ES-davefx-medium',
  suggestion_count: 3,
  whisper_model: 'base',
  updated_at: '2026-03-20T10:00:00Z',
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
  await page.route('/api/conversations/1', (route) =>
    route.fulfill({ json: mockConversation }),
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
  await page.route('/api/conversations/1', (route) => {
    if (route.request().method() === 'PATCH') {
      return route.fulfill({ json: { ...mockConversation, status: 'completed' } })
    }
    return route.fulfill({ json: mockConversation })
  })
}
