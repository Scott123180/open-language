import type { Page, Route } from '@playwright/test'

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

// ── Flashcards by practice language (006) ─────────────────────────────────────

export type PracticeLanguageId = 'es' | 'de'

/** Serve the stored practice language and the language catalogue the Flashcards pages load. */
export async function mockPracticeLanguageSetting(page: Page, language: PracticeLanguageId) {
  await page.route('/api/settings', (route) =>
    route.fulfill({ json: { ...mockSettings, target_language: language } }),
  )
  await mockPracticeLanguagesApi(page)
}

/** Matches the deck collection with any query string, but not `/decks/{id}`. */
export const isDeckCollection = (url: URL) => url.pathname === '/api/flashcards/decks'

/**
 * The `language` a flashcards collection request carries. A request without one is answered
 * 422, as the backend does, so a page that forgets it fails its test.
 */
export function requestedLanguage(route: Route): string | null {
  const language = new URL(route.request().url()).searchParams.get('language')
  if (language === null) {
    void route.fulfill({ status: 422, json: { detail: 'language is required' } })
  }
  return language
}

export const mockGermanWords = [
  {
    id: 11,
    word: 'Haus',
    translation: 'house',
    target_language: 'de',
    native_language: 'en',
    classification: 'not_practiced',
    manual_override: false,
    saved_at: '2026-03-23T10:00:00Z',
    source_conversation_id: 3,
  },
  {
    id: 12,
    word: 'Straße',
    translation: 'street',
    target_language: 'de',
    native_language: 'en',
    classification: 'difficult',
    manual_override: false,
    saved_at: '2026-03-24T10:00:00Z',
    source_conversation_id: 3,
  },
]

// ── Podcasts (007 contracts §1, §2, §6, §7) ───────────────────────────────────

const LUCIA_HOST = {
  slot: 'lead',
  name: 'Lucía',
  personality_id: 'enthusiast',
  voice_key: 'es_AR-daniela-high',
  show_role: 'host',
  angle: null,
}

const MARCO_HOST = {
  slot: 'second',
  name: 'Marco',
  personality_id: 'dry_sceptic',
  voice_key: 'es_ES-davefx-medium',
  show_role: 'co_host',
  angle: null,
}

/** A ready-made show as `GET /api/podcasts/catalog` serves it. */
export const showDraftFixture = {
  source: 'ready_made',
  show_id: 'weekend-food-talk',
  title: 'Weekend Food Talk',
  premise: 'Two food lovers swap weekend cooking wins and disasters.',
  topic: 'food',
  learner_role: 'guest',
  language: 'es',
  hosts: [LUCIA_HOST, MARCO_HOST],
}

const OTHER_SHOWS = [
  ['tech-for-normal-people', 'Tech for Normal People', 'technology', 'caller'],
  ['game-day', 'Game Day', 'sport', 'co_host'],
  ['on-the-road', 'On the Road', 'travel', 'guest'],
  ['screen-and-sound', 'Screen & Sound', 'film and music', 'co_host'],
  ['nine-to-five', 'Nine to Five', 'work life', 'caller'],
].map(([show_id, title, topic, learner_role]) => ({
  ...showDraftFixture,
  show_id,
  title,
  topic,
  learner_role,
  premise: `A show about ${topic}.`,
}))

export const mockPodcastCatalog = {
  language: 'es',
  language_name: 'Spanish',
  formats: [
    { format_id: 'one_host', label: 'One host', host_count: 1, is_learner_speaking: true, description: 'You and one host.' },
    { format_id: 'panel', label: 'Panel', host_count: 2, is_learner_speaking: true, description: 'You and two hosts.' },
    { format_id: 'listen', label: 'Listen', host_count: 2, is_learner_speaking: false, description: 'Two hosts talk; you listen.' },
  ],
  lengths: [
    { length_id: 'short', label: 'Short', target_host_lines: 10, is_default: false },
    { length_id: 'medium', label: 'Medium', target_host_lines: 20, is_default: true },
    { length_id: 'long', label: 'Long', target_host_lines: 40, is_default: false },
  ],
  personalities: [
    { personality_id: 'enthusiast', label: 'Enthusiast', description: 'Excited about everything and quick to share.' },
    { personality_id: 'dry_sceptic', label: 'Dry sceptic', description: 'Unimpressed until convinced, with a dry sense of humour.' },
    { personality_id: 'joker', label: 'Joker', description: 'Never misses a chance for a joke.' },
  ],
  shows: [showDraftFixture, ...OTHER_SHOWS],
  voices: { installed_count: 2, shared_voice_notice: null as string | null, unavailable_message: null as string | null },
}

export const mockPodcastPreferences = {
  last_format: 'one_host',
  is_show_text_on: false,
  interests: [] as string[],
  learner_name: null as string | null,
}

const EPISODE_HOSTS = [
  { host_id: 11, ...LUCIA_HOST, personality_label: 'Enthusiast', is_voice_available: true, voice_unavailable_message: null as string | null },
  { host_id: 12, ...MARCO_HOST, personality_label: 'Dry sceptic', is_voice_available: true, voice_unavailable_message: null as string | null },
]

const FORMAT_LABELS: Record<string, string> = { one_host: 'One host', panel: 'Panel', listen: 'Listen' }

/** A new episode of Weekend Food Talk with no lines yet, awaiting its opening. */
export function episodeFixture(format: 'one_host' | 'panel' | 'listen') {
  return {
    conversation_id: 57,
    status: 'active',
    language: 'es',
    language_name: 'Spanish',
    native_language_name: 'English',
    show: {
      title: showDraftFixture.title,
      premise: showDraftFixture.premise,
      topic: showDraftFixture.topic,
      learner_role: 'guest',
      source: 'ready_made',
      show_id: showDraftFixture.show_id,
    },
    format,
    format_label: FORMAT_LABELS[format],
    length: 'short',
    target_host_lines: 10,
    learner_name: null as string | null,
    hosts: format === 'one_host' ? EPISODE_HOSTS.slice(0, 1) : EPISODE_HOSTS,
    shared_voice_notice: null as string | null,
    turn: 'hosts',
    awaiting: 'opening' as string | null,
    can_jump_in: false,
    can_pass: false,
    lines: [] as unknown[],
  }
}

export interface LineFixture {
  message_id: number
  host_id: number | null
  content: string
  intent?: string | null
  invites_learner?: boolean
}

/** A line object as `line` frames and `GET /api/podcasts/episodes/{id}` carry it. */
export function lineFixture(line: LineFixture) {
  return {
    speaker: line.host_id === null ? 'learner' : 'host',
    intent: null,
    invites_learner: false,
    is_revealed: false,
    created_at: '2026-09-28T10:00:00Z',
    ...line,
  }
}

/** One `line` frame followed by its `done` frame, with the turn state after the line. */
export function lineFrame(line: LineFixture, turn: string, awaiting: string | null = null) {
  return [
    { event: 'line', line: lineFixture(line), turn, awaiting },
    { done: true, turn, awaiting, can_jump_in: false, can_pass: false },
  ]
}

/** Build an SSE body from frames, e.g. `makeLineSseBody(lineFrame(...))`. */
export function makeLineSseBody(frames: unknown[]): string {
  return frames.map((frame) => `data: ${JSON.stringify(frame)}\n\n`).join('')
}

export interface PodcastRouteOptions {
  episode?: ReturnType<typeof episodeFixture>
  preferences?: typeof mockPodcastPreferences
  catalog?: typeof mockPodcastCatalog
}

/** Mock the Podcasts, setup and episode screens' reads. Line streams are mocked per test. */
export async function mockPodcastApis(page: Page, options: PodcastRouteOptions = {}) {
  const episode = options.episode ?? episodeFixture('one_host')
  await page.route('/api/podcasts/catalog', (route) => route.fulfill({ json: options.catalog ?? mockPodcastCatalog }))
  await page.route('/api/podcasts/preferences', (route) => route.fulfill({ json: options.preferences ?? mockPodcastPreferences }))
  await page.route('/api/podcasts/episodes', (route) =>
    route.request().method() === 'POST' ? route.fulfill({ status: 201, json: episode }) : route.fulfill({ json: [] }),
  )
  await page.route(`/api/podcasts/episodes/${episode.conversation_id}`, (route) => route.fulfill({ json: episode }))
  await page.route(`/api/podcasts/episodes/${episode.conversation_id}/session`, (route) =>
    route.fulfill({ status: 202, json: { status: 'warming' } }),
  )
  await page.route('/api/audio/tts/**', (route) => route.fulfill({ status: 200, body: '' }))
  await page.route('/api/settings', (route) => route.fulfill({ json: mockSettings }))
  await mockConversationLevelsApi(page)
  await mockPracticeLanguagesApi(page)
}

/** Serve `bodies` in order to successive POSTs of one episode action (e.g. `next`). */
export async function mockLineStream(page: Page, action: string, bodies: string[], conversationId = 57) {
  const requests: unknown[] = []
  await page.route(`/api/podcasts/episodes/${conversationId}/${action}`, (route) => {
    requests.push(route.request().postDataJSON?.() ?? null)
    const body = bodies[Math.min(requests.length - 1, bodies.length - 1)]
    return route.fulfill({ status: 200, headers: { 'Content-Type': 'text/event-stream' }, body })
  })
  return { requests }
}

// ── Conversation summary (007 US6, contracts §9) ──────────────────────────────

export function summaryFixture(conversationId = 1, points = [
  { conversation_language: 'Pides un café con leche.', english: 'You order a white coffee.' },
  { conversation_language: 'Ahora preguntas el precio.', english: 'Now you ask the price.' },
]) {
  return {
    status: 'ready',
    conversation_id: conversationId,
    up_to_message_id: 9,
    conversation_language: 'es',
    conversation_language_name: 'Spanish',
    native_language_name: 'English',
    points,
  }
}

export const TOO_EARLY_SUMMARY = {
  status: 'too_early',
  message: "There's nothing to summarise yet. Come back after the next line.",
}

/** Settings whose summary language follows the learner's PUTs, and the PUT bodies sent. */
export async function mockSummarySettings(page: Page, initial: 'conversation' | 'native' = 'conversation') {
  const puts: unknown[] = []
  let summaryLanguage = initial
  await page.route('/api/settings', (route) => {
    if (route.request().method() === 'PUT') {
      const body = route.request().postDataJSON()
      puts.push(body)
      summaryLanguage = body.summary_language ?? summaryLanguage
    }
    return route.fulfill({ json: { ...mockSettings, summary_language: summaryLanguage } })
  })
  return { puts }
}

export const generatedShowFixture = {
  ...showDraftFixture,
  source: 'generated',
  show_id: null as string | null,
  title: 'Night Shift Abroad',
  premise: 'Two nurses swap stories about working far from home.',
  topic: 'living abroad as a nurse',
}
export const IDEA_DECLINED = "That idea can't become a show here. Try a different topic, or press Surprise me."
export const IDEA_NEEDED = "Type a few words about the show you'd like, or press Surprise me."

/** Serve `drafts` in order to successive POSTs of `/shows/generate`, recording each body.
 * An entry with a `detail` is served as the 422 refusal it describes. */
export async function mockShowGeneration(page: Page, drafts: unknown[]) {
  const requests: Record<string, unknown>[] = []
  await page.route('/api/podcasts/shows/generate', (route) => {
    requests.push(route.request().postDataJSON())
    const draft = drafts[Math.min(requests.length, drafts.length) - 1] as { detail?: string }
    return draft.detail ? route.fulfill({ status: 422, json: { detail: draft.detail, can_surprise: true } }) : route.fulfill({ json: draft })
  })
  return requests
}
