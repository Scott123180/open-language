import { useEffect, useState } from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import type { PodcastCatalog, SeriesSummary, ShowDraft, ShowListing } from '../../services/podcastsApi'
import type { SetupDraft } from './useShowDraft'

export const SHOW_UNAVAILABLE = "That show isn't available any more. Pick another one."
export const DRAFT_GONE = "That show wasn't kept. Generate it again, or pick another one."

/** A show on the setup screen: a draft, with its series and favourite once it is listed. */
export type SetupShowDraft = ShowDraft & { series?: SeriesSummary | null; is_favourite?: boolean }

export interface SetupShow {
  show: SetupShowDraft | undefined
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
  const [params] = useSearchParams()
  const isNamed = params.has('show') || params.has('saved')
  const [draft, setDraft] = useState<SetupDraft | null>(passedDraft(location.state))
  const show = draft?.draft ?? (catalog && findShow(catalog, params))
  const isMissing = catalog !== undefined && show === undefined
  useEffect(() => {
    if (isMissing) navigate('/podcasts', { replace: true, state: { message: isNamed ? SHOW_UNAVAILABLE : DRAFT_GONE } })
  }, [isMissing, isNamed, navigate])
  const replaceDraft = (next: SetupDraft) => {
    setDraft(next)
    navigate(location.pathname, { replace: true, state: next })
  }
  return { show, draft, replaceDraft }
}

/** `?show=` names a ready-made show; `?saved=` a kept show of the learner's own (010). */
function findShow(catalog: PodcastCatalog, params: URLSearchParams): ShowListing | undefined {
  const saved = Number(params.get('saved'))
  if (params.has('saved')) return catalog.my_shows.find((candidate) => candidate.saved_show_id === saved)
  return catalog.shows.find((candidate) => candidate.show_id === params.get('show'))
}

const passedDraft = (state: unknown): SetupDraft | null =>
  state && typeof state === 'object' && 'draft' in state ? (state as SetupDraft) : null
