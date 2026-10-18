import type { HostDraft, SeriesDetail, StartEpisodeBody } from '../../services/podcastsApi'
import type { SetupForm } from './useSetupForm'
import type { SetupShowDraft } from './useSetupShow'
import type { StartEpisode, SeriesStart } from './useStartEpisode'

interface SetupStartInput {
  show: SetupShowDraft
  form: SetupForm
  hosts: HostDraft[]
  starting: StartEpisode
  series: SeriesDetail | undefined
}

/** The setup screen's Start: the chosen kind of episode, with the hosts as the learner left
 * them. A series Start waits for memory; until the detail arrives it counts as pending. */
export function useSetupStart({ show, form, hosts, starting, series }: SetupStartInput): () => void {
  const body: StartEpisodeBody = {
    show: { ...show, hosts },
    format: form.format,
    length: form.length,
    learner_name: form.learnerName.trim(),
    kind: form.kind,
  }
  const seriesStart: SeriesStart | undefined = show.series && form.kind === 'series'
    ? { seriesId: show.series.series_id, memoryStatus: series?.memory_status ?? 'pending' }
    : undefined
  return () => void starting.start(body, seriesStart)
}
