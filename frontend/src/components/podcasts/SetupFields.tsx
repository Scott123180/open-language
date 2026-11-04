import type { PodcastCatalog } from '../../services/podcastsApi'
import type { SetupForm } from '../../hooks/podcasts/useSetupForm'
import FormatFieldset from './FormatFieldset'
import LearnerNameField from './LearnerNameField'
import LengthFieldset from './LengthFieldset'
import SetupVoiceNotice from './SetupVoiceNotice'

interface SetupFieldsProps {
  catalog: PodcastCatalog
  form: SetupForm
  hostCount: number
  /** A continuing series' host names, whose clash with the learner's name is shown. */
  hostNames: string[]
}

/** The format, the length and the learner's name: the setup's everyday choices (FR-005). */
export default function SetupFields({ catalog, form, hostCount, hostNames }: SetupFieldsProps) {
  return (
    <>
      <FormatFieldset formats={catalog.formats} value={form.format} onChange={form.setFormat} />
      <SetupVoiceNotice voices={catalog.voices} hostCount={hostCount} />
      <LengthFieldset lengths={catalog.lengths} value={form.length} onChange={form.setLength} />
      <LearnerNameField value={form.learnerName} onChange={form.setLearnerName} hostNames={hostNames} />
    </>
  )
}
