import type { PodcastCatalog, SeriesDetail, SeriesHostView } from '../../services/podcastsApi'
import type { SetupForm as SetupFormState } from '../../hooks/podcasts/useSetupForm'
import type { SetupShowDraft } from '../../hooks/podcasts/useSetupShow'
import type { StartEpisode } from '../../hooks/podcasts/useStartEpisode'
import { useSetupHosts } from '../../hooks/podcasts/useSetupHosts'
import { useSetupStart } from '../../hooks/podcasts/useSetupStart'
import FormatFieldset from './FormatFieldset'
import LengthFieldset from './LengthFieldset'
import LearnerNameField from './LearnerNameField'
import SeriesHosts from './SeriesHosts'
import SeriesMemoryPanel from './SeriesMemoryPanel'
import SetupActions from './SetupActions'
import SetupHosts from './SetupHosts'
import SetupVoiceNotice from './SetupVoiceNotice'

interface SetupFormProps {
  show: SetupShowDraft
  catalog: PodcastCatalog
  form: SetupFormState
  starting: StartEpisode
  /** The series detail, once loaded, for a show that has one. */
  series: SeriesDetail | undefined
}

/** Everything the learner sees before an episode starts, and the one Start action (FR-005).
 * Once a series has an episode its hosts are fixed: read-only, with no Shuffle (FR-008). */
export default function SetupForm({ show, catalog, form, starting, series }: SetupFormProps) {
  const hostCount = catalog.formats.find((f) => f.format_id === form.format)?.host_count ?? 1
  const hosts = useSetupHosts(show, form.learnerName)
  const seriesHosts = (show.series?.episode_count ?? 0) >= 1 ? series?.hosts ?? listedHosts(show, catalog) : null
  const start = useSetupStart({ show, form, hosts: seriesHosts ? show.hosts : hosts.hosts, starting, series })
  const hostNames = show.hosts.map((host) => host.name)
  return (
    <>
      <p style={{ margin: 0, color: 'var(--color-text)' }}>{show.premise}</p>
      {seriesHosts ? <SeriesSection show={show} catalog={catalog} form={form} hosts={seriesHosts} hostCount={hostCount} series={series} onPlaySample={hosts.playSample} />
        : <SetupHosts controls={hosts} personalities={catalog.personalities} hostCount={hostCount} />}
      <FormatFieldset formats={catalog.formats} value={form.format} onChange={form.setFormat} />
      <SetupVoiceNotice voices={catalog.voices} hostCount={hostCount} />
      <LengthFieldset lengths={catalog.lengths} value={form.length} onChange={form.setLength} />
      <LearnerNameField value={form.learnerName} onChange={form.setLearnerName} hostNames={seriesHosts ? hostNames : []} />
      <SetupActions series={show.series ?? null} starting={starting} onStart={start} hostNames={hostNames} />
    </>
  )
}

interface SeriesSectionProps {
  show: SetupShowDraft
  catalog: PodcastCatalog
  form: SetupFormState
  hosts: SeriesHostView[]
  hostCount: number
  series: SeriesDetail | undefined
  onPlaySample: (host: SeriesHostView) => void
}

/** A continuing series: its fixed hosts with Recast…, then what they remember. */
function SeriesSection({ show, catalog, form, hosts, hostCount, series, onPlaySample }: SeriesSectionProps) {
  const context = { seriesId: show.series!.series_id, language: show.language, learnerName: form.learnerName }
  return (
    <>
      <SeriesHosts hosts={hosts} hostCount={hostCount} personalities={catalog.personalities}
        keepsVoice={catalog.voices.installed_count <= 2} series={context} onPlaySample={onPlaySample} />
      {series && <SeriesMemoryPanel detail={series} />}
    </>
  )
}

/** The series' hosts as the catalogue lists them, while the series detail loads. */
function listedHosts(show: SetupShowDraft, catalog: PodcastCatalog): SeriesHostView[] {
  const labelOf = (id: string) => catalog.personalities.find((p) => p.personality_id === id)?.label ?? id
  return show.hosts.map((host) => ({
    ...host,
    personality_label: labelOf(host.personality_id),
    has_history: true,
    is_new_next_episode: false,
    is_voice_available: true,
    voice_unavailable_message: null,
  }))
}
