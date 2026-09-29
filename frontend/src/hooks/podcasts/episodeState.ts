import type { FeedbackNoteData } from '../../services/api'
import type {
  Awaiting,
  DoneFrame,
  Episode,
  EpisodeLine,
  FeedbackFrame,
  LineFrame,
  Turn,
} from '../../services/podcastsApi'

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
  return { ...state, lines: [...state.lines, frame.line], turn: frame.turn, awaiting: frame.awaiting }
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
  }
}
