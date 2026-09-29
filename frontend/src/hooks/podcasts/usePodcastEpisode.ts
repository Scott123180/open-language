import { useCallback, useEffect, useMemo, useReducer, useRef } from 'react'
import type { Dispatch, MutableRefObject } from 'react'
import * as podcasts from '../../services/podcastsApi'
import type { EpisodeStreamHandlers } from '../../services/podcastsApi'
import { episodeReducer, initialEpisodeState } from './episodeState'
import type { EpisodeAction, EpisodeState } from './episodeState'

type StartStream = (handlers: EpisodeStreamHandlers) => Promise<void>
type RunStream = (start: StartStream, learnerText?: string) => void

export interface EpisodeActions {
  next: () => void
  retry: () => void
  end: () => void
  send: (text: string, source: 'voice' | 'keyboard', confidence?: number) => void
}

export type PodcastEpisode = EpisodeState & EpisodeActions

/**
 * One episode's turn state machine. The server decides whose turn it is; this hook only relays
 * its frames, asks for the opening and for the reply to the learner by itself, and waits for
 * Continue otherwise (FR-016). One action runs at a time.
 */
export function usePodcastEpisode(conversationId: number): PodcastEpisode {
  const [state, dispatch] = useReducer(episodeReducer, initialEpisodeState)
  const pendingRef = useRef(false)
  const run = useStreamRunner(dispatch, pendingRef)
  useLoadedEpisode(conversationId, dispatch)
  const actions = useEpisodeActions(conversationId, run)
  useAutoNext(state, actions.next)
  return { ...state, ...actions }
}

function streamHandlers(dispatch: Dispatch<EpisodeAction>, learnerText?: string): EpisodeStreamHandlers {
  return {
    onLine: (frame) => dispatch({ type: 'line', frame }),
    onDone: (frame) => dispatch({ type: 'done', frame }),
    onError: (message) => dispatch({ type: 'error', message }),
    onUserSaved: (messageId) => dispatch({ type: 'learner', messageId, content: learnerText ?? '' }),
    onFeedback: (frame) => dispatch({ type: 'feedback', frame }),
  }
}

function useStreamRunner(
  dispatch: Dispatch<EpisodeAction>,
  pendingRef: MutableRefObject<boolean>,
): RunStream {
  return useCallback(
    (start, learnerText) => {
      if (pendingRef.current) return
      pendingRef.current = true
      dispatch({ type: 'pending' })
      void start(streamHandlers(dispatch, learnerText)).finally(() => {
        pendingRef.current = false
        dispatch({ type: 'settled' })
      })
    },
    [dispatch, pendingRef],
  )
}

function useLoadedEpisode(conversationId: number, dispatch: Dispatch<EpisodeAction>): void {
  useEffect(() => {
    let isCurrent = true
    podcasts
      .getEpisode(conversationId)
      .then((episode) => {
        if (!isCurrent) return
        dispatch({ type: 'loaded', episode })
        if (episode.status !== 'completed') void podcasts.warmEpisodeSession(conversationId)
      })
      .catch((e: Error) => isCurrent && dispatch({ type: 'error', message: e.message }))
    return () => {
      isCurrent = false
    }
  }, [conversationId, dispatch])
}

function useEpisodeActions(conversationId: number, run: RunStream): EpisodeActions {
  return useMemo(() => {
    const next = () => run((handlers) => podcasts.streamEpisodeNext(conversationId, handlers))
    return {
      next,
      retry: next,
      end: () => run((handlers) => podcasts.streamEpisodeEnd(conversationId, handlers)),
      send: (text, source, confidence) => {
        const body = { content: text, input_source: source, transcription_confidence: confidence }
        run((handlers) => podcasts.streamEpisodeMessage(conversationId, body, handlers), text)
      },
    }
  }, [conversationId, run])
}

/** The opening, and the reply to the learner, are asked for without a press (FR-016). */
function useAutoNext(state: EpisodeState, next: () => void): void {
  const isAutomatic = state.awaiting === 'opening' || state.awaiting === 'reply'
  const shouldAsk =
    state.episode !== null && state.turn === 'hosts' && isAutomatic && !state.isPending && !state.error
  useEffect(() => {
    if (shouldAsk) next()
  }, [shouldAsk, next])
}
