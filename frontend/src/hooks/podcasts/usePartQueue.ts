import { useCallback, useState } from 'react'
import type { LinePartEvent } from '../../services/podcastsApi'

export interface PartQueue {
  /** The part playing now, or null. */
  current: string | null
  add: (part: LinePartEvent) => void
  ended: () => void
  stop: () => void
}

interface QueueState {
  streamId: string | null
  nextIndex: number
  waiting: Map<number, string>
  current: string | null
}

const EMPTY: QueueState = { streamId: null, nextIndex: 0, waiting: new Map(), current: null }

/** Plays a streamed line's parts in index order, each after the one before it ends, and a late
 * part as soon as it arrives (011 research R13.8). */
export function usePartQueue(): PartQueue {
  const [queue, setQueue] = useState<QueueState>(EMPTY)
  const add = useCallback((part: LinePartEvent) => setQueue((state) => advance(added(state, part))), [])
  const ended = useCallback(() => setQueue((state) => advance({ ...state, current: null })), [])
  const stop = useCallback(() => setQueue(EMPTY), [])
  return { current: queue.current, add, ended, stop }
}

function added(state: QueueState, part: LinePartEvent): QueueState {
  if (part.audio_url === null) return state
  const fresh = state.streamId === part.stream_id ? state : { ...EMPTY, streamId: part.stream_id }
  const waiting = new Map(fresh.waiting).set(part.index, part.audio_url)
  return { ...fresh, waiting, current: state.streamId === part.stream_id ? state.current : null }
}

function advance(state: QueueState): QueueState {
  const next = state.waiting.get(state.nextIndex)
  if (state.current !== null || next === undefined) return state
  const waiting = new Map(state.waiting)
  waiting.delete(state.nextIndex)
  return { ...state, waiting, current: next, nextIndex: state.nextIndex + 1 }
}
