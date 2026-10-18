import { useReducer, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import * as podcasts from '../../services/podcastsApi'
import type { MemoryStatus, StartEpisodeBody } from '../../services/podcastsApi'
import { catchUpReducer, IDLE, outcomeAction, type CatchUpState } from './catchUpState'

const START_FAILED = 'The episode could not start. Please try again.'

/** The series a Start continues, and whether its hosts have caught up on it. */
export interface SeriesStart {
  seriesId: number
  memoryStatus: MemoryStatus
}

export interface StartEpisode {
  start: (body: StartEpisodeBody, series?: SeriesStart) => Promise<void>
  isStarting: boolean
  error: string | null
  catchUp: CatchUpState
  retry: () => Promise<void>
  startWithoutUpdate: () => Promise<void>
}

/** Start an episode and open it. A series Start whose memory is behind first waits for the
 * hosts to catch up, and on failure offers Try again or Start without it (research R6). */
export function useStartEpisode(): StartEpisode {
  const [catchUp, dispatch] = useReducer(catchUpReducer, IDLE)
  const pending = useRef<{ body: StartEpisodeBody; seriesId: number } | null>(null)
  const { open, isStarting, error } = useOpenEpisode()
  const waitThenOpen = async () => {
    const { body, seriesId } = pending.current!
    dispatch({ type: 'wait' })
    const action = outcomeAction(await podcasts.catchUpSeriesMemory(seriesId, { wait: true }))
    dispatch(action)
    if (action.type === 'caughtUp') await open(body)
  }
  const start = async (body: StartEpisodeBody, series?: SeriesStart) => {
    if (!series || series.memoryStatus === 'up_to_date') return open(body)
    pending.current = { body, seriesId: series.seriesId }
    await waitThenOpen()
  }
  const startWithoutUpdate = () => open(pending.current!.body)
  return { start, isStarting: isStarting || catchUp.phase === 'catchingUp', error, catchUp, retry: waitThenOpen, startWithoutUpdate }
}

/** Create the episode and navigate to it; a refusal is shown in the server's plain words. */
function useOpenEpisode() {
  const navigate = useNavigate()
  const [isStarting, setIsStarting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const open = async (body: StartEpisodeBody) => {
    setIsStarting(true)
    setError(null)
    try {
      const episode = await podcasts.startEpisode(body)
      navigate(`/podcasts/episodes/${episode.conversation_id}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : START_FAILED)
      setIsStarting(false)
    }
  }
  return { open, isStarting, error }
}
