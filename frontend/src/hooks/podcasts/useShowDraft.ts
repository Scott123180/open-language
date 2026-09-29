import { useState } from 'react'
import * as podcasts from '../../services/podcastsApi'
import type { ShowDraft } from '../../services/podcastsApi'

/** A show that is not in the catalogue, carried to setup in router state. Nothing is stored
 * until an episode starts, so the idea and the titles so far travel with it (FR-021). */
export interface SetupDraft {
  draft: ShowDraft
  idea: string | null
  previousTitles: string[]
}

export interface ShowDraftRequests {
  generate: (idea: string) => Promise<SetupDraft | null>
  surprise: () => Promise<SetupDraft | null>
  anotherVersion: (current: SetupDraft) => Promise<SetupDraft | null>
  isPending: boolean
  error: string | null
}

const FALLBACK_ERROR = 'The show could not be made. Please try again.'

/** Generate, Surprise me and Another version; a refusal keeps the server's plain words. */
export function useShowDraft(): ShowDraftRequests {
  const [isPending, setIsPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const run = async (request: () => Promise<SetupDraft>): Promise<SetupDraft | null> => {
    setIsPending(true)
    setError(null)
    try {
      return await request()
    } catch (e) {
      setError(e instanceof Error ? e.message : FALLBACK_ERROR)
      return null
    } finally {
      setIsPending(false)
    }
  }
  return { ...draftRequests(run), isPending, error }
}

type Run = (request: () => Promise<SetupDraft>) => Promise<SetupDraft | null>

function draftRequests(run: Run): Pick<ShowDraftRequests, 'generate' | 'surprise' | 'anotherVersion'> {
  return {
    generate: (idea) => run(async () => ({ draft: await podcasts.generateShow(idea, []), idea, previousTitles: [] })),
    surprise: () => run(async () => ({ draft: await podcasts.surpriseShow(), idea: null, previousTitles: [] })),
    anotherVersion: (current) => {
      const previousTitles = [...current.previousTitles, current.draft.title]
      return run(async () => ({ draft: await podcasts.generateShow(current.idea ?? '', previousTitles), idea: current.idea, previousTitles }))
    },
  }
}
