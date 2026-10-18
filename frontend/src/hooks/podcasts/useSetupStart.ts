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

/** The setup screen's Start: the next series episode, with the hosts as the learner left them.
 * Until the series detail arrives its memory counts as pending, so Start waits to be safe. */
export function useSetupStart({ show, form, hosts, starting, series }: SetupStartInput): () => void {
  const body: StartEpisodeBody = {
    show: { ...show, hosts },
    format: form.format,
    length: form.length,
    learner_name: form.learnerName.trim(),
    kind: 'series',
  }
  const seriesStart: SeriesStart | undefined = show.series
    ? { seriesId: show.series.series_id, memoryStatus: series?.memory_status ?? 'pending' }
    : undefined
  return () => void starting.start(body, seriesStart)
}
