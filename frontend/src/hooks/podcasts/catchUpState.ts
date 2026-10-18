import type { CatchUpResult } from '../../services/podcastsApi'

/** Where a series Start is while the hosts catch up on the last episodes (010 research R6). */
export type CatchUpPhase = 'idle' | 'catchingUp' | 'failed' | 'timedOut'

export interface CatchUpState {
  phase: CatchUpPhase
  /** The provider's message on failure, or the server's timeout sentence. */
  detail: string | null
}

export type CatchUpAction =
  | { type: 'wait' }
  | { type: 'caughtUp' }
  | { type: 'failed'; detail: string }
  | { type: 'timedOut'; detail: string }

export const IDLE: CatchUpState = { phase: 'idle', detail: null }
const TIMED_OUT_DETAIL = "It's taking longer than usual."
const FAILED_DETAIL = 'Please try again.'

export function catchUpReducer(_state: CatchUpState, action: CatchUpAction): CatchUpState {
  switch (action.type) {
    case 'wait':
      return { phase: 'catchingUp', detail: null }
    case 'failed':
      return { phase: 'failed', detail: action.detail }
    case 'timedOut':
      return { phase: 'timedOut', detail: action.detail }
    default:
      return IDLE
  }
}

/** The action a finished wait leads to. */
export function outcomeAction(result: CatchUpResult): CatchUpAction {
  if (result.status === 'failed') return { type: 'failed', detail: result.detail ?? FAILED_DETAIL }
  if (result.status === 'timed_out') return { type: 'timedOut', detail: result.detail ?? TIMED_OUT_DETAIL }
  return { type: 'caughtUp' }
}
