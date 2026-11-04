import type { PodcastCatalog, PodcastFormatId, SeriesDetail, SeriesSettings } from '../../services/podcastsApi'
import { useExpertGuest, useGuest } from './useGuest'
import type { GuestControls } from './useGuest'
import { useScopedSetupForm } from './useScopedSetupForm'
import { useSeriesScopes } from './useSeriesScopes'
import type { SeriesScopes } from './useSeriesScopes'
import type { SetupForm } from './useSetupForm'
import type { SetupShowDraft } from './useSetupShow'

export interface SeriesSetup {
  /** The form, its series settings asking for a scope on a continuing series. */
  form: SetupForm
  scopes: SeriesScopes
  guest: GuestControls
}

/** A series setup's scopes and guest (011 FR-016, FR-024a). On a series' first episode, or a
 * one-off, nothing is asked and nobody is a guest. */
export function useSeriesSetup(show: SetupShowDraft, catalog: PodcastCatalog, form: SetupForm, series: SeriesDetail | undefined): SeriesSetup {
  const isContinuing = form.kind === 'series' && (show.series?.episode_count ?? 0) >= 1
  const usual = isContinuing ? series?.usual_settings ?? null : null
  const scopes = useSeriesScopes(usual)
  const scoped = useScopedSetupForm(form, scopes)
  const guest = useGuest(show.series?.series_id ?? null, show.language, form.learnerName)
  const isWanted = isExpertWanted(catalog, usual, form.format, scopes)
  useExpertGuest(guest, { isWanted, format: form.format, expertId: series?.second_role_personality_id ?? null })
  return { form: scoped, scopes, guest }
}

/** A One host series made two-host for this episode only gets the show's expert as a guest;
 * from now on, the series' own second host joins instead (011 R12). */
function isExpertWanted(catalog: PodcastCatalog, usual: SeriesSettings | null, format: PodcastFormatId, scopes: SeriesScopes): boolean {
  const hostCount = (id: PodcastFormatId) => catalog.formats.find((f) => f.format_id === id)?.host_count ?? 1
  if (usual === null || hostCount(usual.format) !== 1) return false
  return hostCount(format) === 2 && scopes.scopeOf('format') === 'this-episode'
}
