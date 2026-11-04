import type { HostDraft, SeriesDetail, SeriesSettingName, StartEpisodeBody } from '../../services/podcastsApi'
import type { SetupForm } from './useSetupForm'
import type { SetupShowDraft } from './useSetupShow'
import type { StartEpisode, SeriesStart } from './useStartEpisode'

interface SetupStartInput {
  show: SetupShowDraft
  form: SetupForm
  hosts: HostDraft[]
  starting: StartEpisode
  series: SeriesDetail | undefined
  /** 011: the settings kept for later episodes, and this episode's guest. */
  fromNowOn?: SeriesSettingName[]
  guest?: HostDraft | null
}

/** The setup screen's Start: the chosen kind of episode, with the hosts as the learner left
 * them. A series Start waits for memory; until the detail arrives it counts as pending. */
export function useSetupStart({ show, form, hosts, starting, series, fromNowOn = [], guest = null }: SetupStartInput): () => void {
  const body: StartEpisodeBody = {
    show: { ...show, hosts },
    format: form.format,
    length: form.length,
    learner_name: form.learnerName.trim(),
    kind: form.kind,
    settings: form.settings.requestSettings(),
    ...(fromNowOn.length > 0 && { from_now_on: fromNowOn }),
    ...(guest && { guest }),
  }
  const seriesStart: SeriesStart | undefined = show.series && form.kind === 'series'
    ? { seriesId: show.series.series_id, memoryStatus: series?.memory_status ?? 'pending' }
    : undefined
  return () => void starting.start(body, seriesStart)
}
