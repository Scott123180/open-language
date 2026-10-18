import { useRef, useState } from 'react'
import * as podcasts from '../../services/podcastsApi'
import type { ShowDraft } from '../../services/podcastsApi'

const DISCOVERY_FAILED = "New shows couldn't be found this time. Please try again."
const MAX_AVOID_TITLES = 50

export interface ShowDiscovery {
  suggestions: ShowDraft[]
  find: () => Promise<void>
  isFinding: boolean
  error: string | null
}

/** Find a new show. Each further set avoids every title shown this visit (US5-2). */
export function useShowDiscovery(): ShowDiscovery {
  const [suggestions, setSuggestions] = useState<ShowDraft[]>([])
  const [isFinding, setFinding] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const shown = useRef<string[]>([])
  const find = async () => {
    setFinding(true)
    setError(null)
    try {
      const found = await podcasts.discoverShows(shown.current.slice(-MAX_AVOID_TITLES))
      shown.current = [...shown.current, ...found.map((show) => show.title)]
      setSuggestions(found)
    } catch (e) {
      setError(e instanceof Error ? e.message : DISCOVERY_FAILED)
    }
    setFinding(false)
  }
  return { suggestions, find, isFinding, error }
}
