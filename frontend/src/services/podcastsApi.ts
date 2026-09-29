// ---------------------------------------------------------------------------
// Podcast API types (mirror specs/007-podcast-mode/contracts/api.md §1, §2, §6)
// ---------------------------------------------------------------------------

export type PodcastFormatId = 'one_host' | 'panel' | 'listen'
export type EpisodeLengthId = 'short' | 'medium' | 'long'
export type HostSlot = 'lead' | 'second'
export type LearnerRole = 'guest' | 'co_host' | 'caller'
export type ShowSource = 'ready_made' | 'generated' | 'surprise'
export type LineIntent = 'open' | 'greet' | 'discuss' | 'wrap_up' | 'sign_off'

/** Whose turn it is: the hosts', the learner's, or nobody's once the episode has finished. */
export type Turn = 'hosts' | 'learner' | 'finished'
/** At the hosts' turn: the opening, a reply to the learner, or the next line on Continue. */
export type Awaiting = 'opening' | 'reply' | 'continue' | null

export interface PodcastFormatOption {
  format_id: PodcastFormatId
  label: string
  host_count: number
  is_learner_speaking: boolean
  description: string
}

export interface EpisodeLengthOption {
  length_id: EpisodeLengthId
  label: string
  target_host_lines: number
  is_default: boolean
}

export interface PersonalityOption {
  personality_id: string
  label: string
  description: string
}

export interface HostDraft {
  slot: HostSlot
  name: string
  personality_id: string
  voice_key: string
  show_role: string
  angle: string | null
}

export interface ShowDraft {
  source: ShowSource
  show_id: string | null
  title: string
  premise: string
  topic: string
  learner_role: LearnerRole
  language: string
  hosts: HostDraft[]
}

export interface CatalogVoices {
  installed_count: number
  shared_voice_notice: string | null
  unavailable_message: string | null
}

export interface PodcastCatalog {
  language: string
  language_name: string
  formats: PodcastFormatOption[]
  lengths: EpisodeLengthOption[]
  personalities: PersonalityOption[]
  shows: ShowDraft[]
  voices: CatalogVoices
}

export interface PodcastPreferences {
  last_format: PodcastFormatId
  is_show_text_on: boolean
  interests: string[]
  learner_name: string | null
}

export interface EpisodeHost {
  host_id: number
  slot: HostSlot
  name: string
  personality_id: string
  personality_label: string
  voice_key: string
  show_role: string
  is_voice_available: boolean
  voice_unavailable_message: string | null
}

export interface EpisodeLine {
  message_id: number
  speaker: 'host' | 'learner'
  host_id: number | null
  content: string
  intent: LineIntent | null
  invites_learner: boolean
  is_revealed: boolean
  created_at: string
}

export interface EpisodeShow {
  title: string
  premise: string
  topic: string
  learner_role: LearnerRole
  source: ShowSource
  show_id: string | null
}

export interface Episode {
  conversation_id: number
  status: 'active' | 'completed'
  language: string
  language_name: string
  native_language_name: string
  show: EpisodeShow
  format: PodcastFormatId
  format_label: string
  length: EpisodeLengthId
  target_host_lines: number
  learner_name: string | null
  hosts: EpisodeHost[]
  shared_voice_notice: string | null
  turn: Turn
  awaiting: Awaiting
  can_jump_in: boolean
  can_pass: boolean
  lines: EpisodeLine[]
}

/** One row of `GET /api/podcasts/episodes`, for labelling Past Chats. */
export interface EpisodeSummaryRow {
  conversation_id: number
  show_title: string
  format: PodcastFormatId
  format_label: string
  host_names: string[]
  language: string
  language_name: string
  status: 'active' | 'completed'
}

// ---------------------------------------------------------------------------
// Requests
// ---------------------------------------------------------------------------

const BASE = '/api/podcasts'

export interface StartEpisodeBody {
  show: ShowDraft
  format: PodcastFormatId
  length: EpisodeLengthId
  learner_name?: string
}

export type PreferencesUpdate = Partial<Pick<PodcastPreferences, 'is_show_text_on' | 'interests' | 'learner_name'>>

async function readError(res: Response): Promise<string> {
  const body = await res.json().catch(() => ({}))
  return body.detail ?? `HTTP ${res.status}`
}

async function podcastFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!res.ok) throw new Error(await readError(res))
  return res.json() as Promise<T>
}

const jsonBody = (method: string, body: unknown): RequestInit => ({ method, body: JSON.stringify(body) })

export const getPodcastCatalog = (): Promise<PodcastCatalog> => podcastFetch('/catalog')

export const getPodcastPreferences = (): Promise<PodcastPreferences> => podcastFetch('/preferences')

export const updatePodcastPreferences = (updates: PreferencesUpdate): Promise<PodcastPreferences> =>
  podcastFetch('/preferences', jsonBody('PUT', updates))

export const startEpisode = (body: StartEpisodeBody): Promise<Episode> =>
  podcastFetch('/episodes', jsonBody('POST', body))

export const listEpisodes = (): Promise<EpisodeSummaryRow[]> => podcastFetch('/episodes')

export const getEpisode = (conversationId: number): Promise<Episode> =>
  podcastFetch(`/episodes/${conversationId}`)

export const getEpisodeSuggestions = (conversationId: number): Promise<{ suggestions: string[] }> =>
  podcastFetch(`/episodes/${conversationId}/suggestions`, { method: 'POST' })

/** FR-043: a tapped Listen line stays revealed for the rest of the episode. */
export const revealLine = async (conversationId: number, messageId: number): Promise<void> => {
  const res = await fetch(`${BASE}/episodes/${conversationId}/lines/${messageId}/reveal`, { method: 'POST' })
  if (!res.ok) throw new Error(await readError(res))
}

/** Get the episode's session ready before the next line. Invisible, so failures are ignored. */
export const warmEpisodeSession = async (conversationId: number): Promise<void> => {
  try {
    await fetch(`${BASE}/episodes/${conversationId}/session`, { method: 'POST' })
  } catch {
    // Deliberately silent: the next line reports any problem with its normal message.
  }
}

// ---------------------------------------------------------------------------
// Line streams (contracts §7)
// ---------------------------------------------------------------------------

export interface LineFrame {
  event: 'line'
  line: EpisodeLine
  turn: Turn
  awaiting: Awaiting
}

export interface DoneFrame {
  done: true
  turn: Turn
  awaiting: Awaiting
  can_jump_in?: boolean
  can_pass?: boolean
}

export interface EpisodeStreamHandlers {
  onLine: (frame: LineFrame) => void
  onDone: (frame: DoneFrame) => void
  onError: (message: string) => void
  onUserSaved?: (messageId: number) => void
  onFeedback?: (data: FeedbackFrame) => void
}

export interface FeedbackFrame {
  message_id: number
  awaiting_retry: boolean
  notes: import('./api').FeedbackNoteData[]
}

export interface LearnerMessageBody {
  content: string
  input_source: 'voice' | 'keyboard'
  transcription_confidence?: number
}

function dispatchFrame(frame: Record<string, unknown>, handlers: EpisodeStreamHandlers): void {
  if (frame.error !== undefined) handlers.onError(frame.error as string)
  else if (frame.done) handlers.onDone(frame as unknown as DoneFrame)
  else if (frame.event === 'line') handlers.onLine(frame as unknown as LineFrame)
  else if (frame.event === 'user_message_saved') handlers.onUserSaved?.(frame.message_id as number)
  else if (frame.event === 'feedback') handlers.onFeedback?.(frame as unknown as FeedbackFrame)
}

function dispatchChunk(lines: string[], handlers: EpisodeStreamHandlers): void {
  for (const line of lines) {
    if (!line.startsWith('data: ')) continue
    try {
      dispatchFrame(JSON.parse(line.slice(6)), handlers)
    } catch {
      // A malformed frame is skipped; the done or error frame still arrives.
    }
  }
}

async function readEpisodeStream(res: Response, handlers: EpisodeStreamHandlers): Promise<void> {
  const reader = res.body?.getReader()
  if (!reader) return handlers.onError('No response body')
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''
    dispatchChunk(lines, handlers)
  }
}

async function streamEpisodeAction(
  path: string,
  handlers: EpisodeStreamHandlers,
  body?: unknown,
): Promise<void> {
  const init: RequestInit = { method: 'POST' }
  if (body !== undefined) Object.assign(init, jsonBody('POST', body), { headers: { 'Content-Type': 'application/json' } })
  const res = await fetch(`${BASE}${path}`, init)
  if (!res.ok) return handlers.onError(await readError(res))
  await readEpisodeStream(res, handlers)
}

export const streamEpisodeNext = (conversationId: number, handlers: EpisodeStreamHandlers) =>
  streamEpisodeAction(`/episodes/${conversationId}/next`, handlers)

export const streamEpisodePass = (conversationId: number, handlers: EpisodeStreamHandlers) =>
  streamEpisodeAction(`/episodes/${conversationId}/pass`, handlers)

export const streamEpisodeEnd = (conversationId: number, handlers: EpisodeStreamHandlers) =>
  streamEpisodeAction(`/episodes/${conversationId}/end`, handlers)

export const streamEpisodeMessage = (
  conversationId: number,
  body: LearnerMessageBody,
  handlers: EpisodeStreamHandlers,
) => streamEpisodeAction(`/episodes/${conversationId}/message`, handlers, body)
