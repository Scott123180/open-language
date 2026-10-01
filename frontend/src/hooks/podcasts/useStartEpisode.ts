import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import * as podcasts from '../../services/podcastsApi'
import type { StartEpisodeBody } from '../../services/podcastsApi'

export interface StartEpisode {
  start: (body: StartEpisodeBody) => Promise<void>
  isStarting: boolean
  error: string | null
}

/** Start an episode and open it; a refusal is shown in the server's plain words. */
export function useStartEpisode(): StartEpisode {
  const navigate = useNavigate()
  const [isStarting, setIsStarting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const start = async (body: StartEpisodeBody) => {
    setIsStarting(true)
    setError(null)
    try {
      const episode = await podcasts.startEpisode(body)
      navigate(`/podcasts/episodes/${episode.conversation_id}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'The episode could not start. Please try again.')
      setIsStarting(false)
    }
  }
  return { start, isStarting, error }
}
