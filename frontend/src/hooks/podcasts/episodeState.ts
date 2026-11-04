import type { FeedbackNoteData } from '../../services/api'
import type {
  Awaiting,
  DoneFrame,
  Episode,
  EpisodeLine,
  FeedbackFrame,
  LineFrame,
  LinePartEvent,
  LineStartedEvent,
  Turn,
} from '../../services/podcastsApi'

/** A host line on its way, one sentence at a time (011 research R13). */
export interface ArrivingLine {
  streamId: string
  hostId: number
  parts: LinePartEvent[]
}

/** The latest streamed line's parts, kept after the line arrives so none goes unplayed. */
export interface StreamParts {
  streamId: string
  parts: LinePartEvent[]
}

/** Everything the episode screen shows, derived from the server's frames (contracts §7). */
export interface EpisodeState {
  episode: Episode | null
  lines: EpisodeLine[]
  turn: Turn
  awaiting: Awaiting
  canJumpIn: boolean
  canPass: boolean
  isPending: boolean
  error: string | null
  notes: Record<number, FeedbackNoteData[]>
  isAwaitingRetry: boolean
  /** Panel: the learner jumped in while the hosts had the floor, so the input bar is open. */
  isJumpingIn: boolean
  arriving: ArrivingLine | null
  streamParts: StreamParts | null
  /** Lines that arrived as parts, whose sound was already played part by part. */
  streamedIds: number[]
  /** The last line lost part-way: its parts must stop playing. */
  lostStreamId: string | null
}

export type EpisodeAction =
  | { type: 'loaded'; episode: Episode }
  | { type: 'pending' }
  | { type: 'settled' }
  | { type: 'line'; frame: LineFrame }
  | { type: 'done'; frame: DoneFrame }
  | { type: 'learner'; messageId: number; content: string }
  | { type: 'feedback'; frame: FeedbackFrame }
  | { type: 'revealed'; messageId: number }
  | { type: 'jumpedIn' }
  | { type: 'error'; message: string }
  | { type: 'lineStarted'; event: LineStartedEvent }
  | { type: 'linePart'; event: LinePartEvent }
  | { type: 'lineLost'; streamId: string }

export const initialEpisodeState: EpisodeState = {
  episode: null,
  lines: [],
  turn: 'hosts',
  awaiting: null,
  canJumpIn: false,
  canPass: false,
  isPending: false,
  error: null,
  notes: {},
  isAwaitingRetry: false,
  isJumpingIn: false,
  arriving: null,
  streamParts: null,
  streamedIds: [],
  lostStreamId: null,
}

const learnerLine = (messageId: number, content: string): EpisodeLine => ({
  message_id: messageId,
  speaker: 'learner',
  host_id: null,
  content,
  intent: null,
  invites_learner: false,
  is_revealed: true,
  created_at: new Date().toISOString(),
})

function loaded(state: EpisodeState, episode: Episode): EpisodeState {
  return {
    ...state,
    episode,
    lines: episode.lines,
    turn: episode.turn,
    awaiting: episode.awaiting,
    canJumpIn: episode.can_jump_in,
    canPass: episode.can_pass,
  }
}

function done(state: EpisodeState, frame: DoneFrame): EpisodeState {
  return {
    ...state,
    turn: frame.turn,
    awaiting: frame.awaiting,
    canJumpIn: frame.can_jump_in ?? false,
    canPass: frame.can_pass ?? false,
    isPending: false,
  }
}

function withLine(state: EpisodeState, frame: LineFrame): EpisodeState {
  const streamedIds = state.arriving ? [...state.streamedIds, frame.line.message_id] : state.streamedIds
  const lines = [...state.lines, frame.line]
  return { ...state, lines, streamedIds, arriving: null, turn: frame.turn, awaiting: frame.awaiting }
}

function withPart(state: EpisodeState, event: LinePartEvent): EpisodeState {
  if (state.arriving?.streamId !== event.stream_id) return state
  const parts = [...state.arriving.parts, event]
  return { ...state, arriving: { ...state.arriving, parts }, streamParts: { streamId: event.stream_id, parts } }
}

function started(state: EpisodeState, event: LineStartedEvent): EpisodeState {
  const streamParts = { streamId: event.stream_id, parts: [] }
  return { ...state, arriving: { streamId: event.stream_id, hostId: event.host_id, parts: [] }, streamParts }
}

function revealed(state: EpisodeState, messageId: number): EpisodeState {
  const lines = state.lines.map((line) =>
    line.message_id === messageId ? { ...line, is_revealed: true } : line,
  )
  return { ...state, lines }
}

function feedback(state: EpisodeState, frame: FeedbackFrame): EpisodeState {
  const notes = { ...state.notes, [frame.message_id]: frame.notes }
  return { ...state, notes, isAwaitingRetry: frame.awaiting_retry }
}

export function episodeReducer(state: EpisodeState, action: EpisodeAction): EpisodeState {
  switch (action.type) {
    case 'loaded': return loaded(state, action.episode)
    case 'pending': return { ...state, isPending: true, error: null, isAwaitingRetry: false, isJumpingIn: false }
    case 'settled': return { ...state, isPending: false }
    case 'line': return withLine(state, action.frame)
    case 'done': return done(state, action.frame)
    case 'learner': return { ...state, lines: [...state.lines, learnerLine(action.messageId, action.content)] }
    case 'feedback': return feedback(state, action.frame)
    case 'revealed': return revealed(state, action.messageId)
    case 'jumpedIn': return { ...state, isJumpingIn: true }
    case 'error': return { ...state, error: action.message, isPending: false }
    case 'lineStarted': return started(state, action.event)
    case 'linePart': return withPart(state, action.event)
    case 'lineLost': return { ...state, arriving: null, lostStreamId: action.streamId }
  }
}
