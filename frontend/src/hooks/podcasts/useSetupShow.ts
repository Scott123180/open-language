import { useEffect, useState } from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import type { PodcastCatalog, ShowDraft } from '../../services/podcastsApi'
import type { SetupDraft } from './useShowDraft'

export const SHOW_UNAVAILABLE = "That show isn't available any more. Pick another one."
export const DRAFT_GONE = "That show wasn't kept. Generate it again, or pick another one."

export interface SetupShow {
  show: ShowDraft | undefined
  /** A generated or surprise show passed in router state; null for a ready-made one. */
  draft: SetupDraft | null
  replaceDraft: (next: SetupDraft) => void
}

/** The show named by `?show=`, or the draft passed in router state. With neither, the learner
 * goes back to Podcasts with a plain message, rather than a setup screen with nothing to set
 * up (research R15). */
export function useSetupShow(catalog: PodcastCatalog | undefined): SetupShow {
  const navigate = useNavigate()
  const location = useLocation()
  const showId = useSearchParams()[0].get('show')
  const [draft, setDraft] = useState<SetupDraft | null>(passedDraft(location.state))
  const show = draft?.draft ?? catalog?.shows.find((candidate) => candidate.show_id === showId)
  const isMissing = catalog !== undefined && show === undefined
  useEffect(() => {
    if (isMissing) navigate('/podcasts', { replace: true, state: { message: showId ? SHOW_UNAVAILABLE : DRAFT_GONE } })
  }, [isMissing, showId, navigate])
  const replaceDraft = (next: SetupDraft) => {
    setDraft(next)
    navigate(location.pathname, { replace: true, state: next })
  }
  return { show, draft, replaceDraft }
}

const passedDraft = (state: unknown): SetupDraft | null =>
  state && typeof state === 'object' && 'draft' in state ? (state as SetupDraft) : null
