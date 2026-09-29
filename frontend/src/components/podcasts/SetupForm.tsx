import ErrorBanner from '../shared/ErrorBanner'
import type { PodcastCatalog, ShowDraft } from '../../services/podcastsApi'
import type { SetupForm as SetupFormState } from '../../hooks/podcasts/useSetupForm'
import type { StartEpisode } from '../../hooks/podcasts/useStartEpisode'
import FormatFieldset from './FormatFieldset'
import LengthFieldset from './LengthFieldset'
import LearnerNameField from './LearnerNameField'
import SetupHosts from './SetupHosts'
import { primaryButtonStyle } from './styles'

interface SetupFormProps {
  show: ShowDraft
  catalog: PodcastCatalog
  form: SetupFormState
  starting: StartEpisode
}

/** Everything the learner sees before an episode starts, and the one Start action (FR-005). */
export default function SetupForm({ show, catalog, form, starting }: SetupFormProps) {
  const hostCount = catalog.formats.find((f) => f.format_id === form.format)?.host_count ?? 1
  const start = () => starting.start({ show, format: form.format, length: form.length, learner_name: form.learnerName.trim() })
  return (
    <>
      <p style={{ margin: 0, color: 'var(--color-text)' }}>{show.premise}</p>
      <SetupHosts show={show} personalities={catalog.personalities} hostCount={hostCount} />
      <FormatFieldset formats={catalog.formats} value={form.format} onChange={form.setFormat} />
      <LengthFieldset lengths={catalog.lengths} value={form.length} onChange={form.setLength} />
      <LearnerNameField value={form.learnerName} onChange={form.setLearnerName} />
      {starting.error && <ErrorBanner message={starting.error} />}
      <button type="button" onClick={start} disabled={starting.isStarting} style={{ ...primaryButtonStyle, alignSelf: 'flex-start' }}>
        Start episode
      </button>
    </>
  )
}
