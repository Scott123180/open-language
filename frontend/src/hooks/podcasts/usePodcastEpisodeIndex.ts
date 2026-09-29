import { useEffect, useState } from 'react'
import * as podcasts from '../../services/podcastsApi'
import type { EpisodeSummaryRow } from '../../services/podcastsApi'

export type EpisodeIndex = Record<number, EpisodeSummaryRow>

/**
 * Which past conversations are podcast episodes, keyed by conversation id (research R17).
 * Past Chats still lists every conversation if this list cannot load.
 */
export function usePodcastEpisodeIndex(): EpisodeIndex {
  const [index, setIndex] = useState<EpisodeIndex>({})
  useEffect(() => {
    let isCurrent = true
    podcasts
      .listEpisodes()
      .then((rows) => isCurrent && setIndex(Object.fromEntries(rows.map((row) => [row.conversation_id, row]))))
      .catch(() => undefined)
    return () => {
      isCurrent = false
    }
  }, [])
  return index
}
