import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import type { PodcastCatalog, ShowDraft } from '../../services/podcastsApi'

export const SHOW_UNAVAILABLE = "That show isn't available any more. Pick another one."

/** The show named by `?show=`. An unknown one sends the learner back to Podcasts with a
 * plain message, rather than a setup screen with nothing to set up (research R15). */
export function useSetupShow(catalog: PodcastCatalog | undefined): ShowDraft | undefined {
  const navigate = useNavigate()
  const showId = useSearchParams()[0].get('show')
  const show = catalog?.shows.find((candidate) => candidate.show_id === showId)
  const isMissing = catalog !== undefined && show === undefined
  useEffect(() => {
    if (isMissing) navigate('/podcasts', { replace: true, state: { message: SHOW_UNAVAILABLE } })
  }, [isMissing, navigate])
  return show
}
