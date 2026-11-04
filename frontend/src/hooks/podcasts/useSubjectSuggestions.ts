import { useCallback, useRef, useState } from 'react'
import { suggestSubjects } from '../../services/podcastsApi'
import type { SubjectShow } from '../../services/podcastsApi'

/** The most subjects already shown that a request may send (data-model §1.4). */
export const SUBJECT_AVOID_MAX = 10

export type SuggestionPhase = 'idle' | 'waiting' | 'shown' | 'empty' | 'error'

export interface SubjectSuggestions {
  phase: SuggestionPhase
  subjects: string[]
  message: string | null
  ask: () => void
}

/** Suggest subjects: each press asks for subjects not covered and not shown yet on this setup
 * (FR-010a). Nothing is asked for until the learner presses. */
export function useSubjectSuggestions(show: SubjectShow, seriesId: number | null): SubjectSuggestions {
  const [phase, setPhase] = useState<SuggestionPhase>('idle')
  const [subjects, setSubjects] = useState<string[]>([])
  const [message, setMessage] = useState<string | null>(null)
  const shownRef = useRef<string[]>([])
  const ask = useCallback(() => {
    setPhase('waiting')
    suggestSubjects(show, seriesId, shownRef.current.slice(-SUBJECT_AVOID_MAX))
      .then(({ subjects: found }) => {
        shownRef.current = [...shownRef.current, ...found]
        setSubjects(found)
        setPhase(found.length > 0 ? 'shown' : 'empty')
      })
      .catch((error: Error) => {
        setMessage(error.message)
        setPhase('error')
      })
  }, [show, seriesId])
  return { phase, subjects, message, ask }
}
