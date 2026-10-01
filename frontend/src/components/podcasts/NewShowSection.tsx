import { useNavigate } from 'react-router-dom'
import { usePodcastPreferences } from '../../hooks/podcasts/usePodcastPreferences'
import { useShowDraft, type SetupDraft } from '../../hooks/podcasts/useShowDraft'
import InterestsEditor from './InterestsEditor'
import ShowGenerator from './ShowGenerator'

/** A show of the learner's own: from an idea or a surprise, shaped by their interests (US4).
 * A made show goes to setup in router state; it is stored only if an episode starts. */
export default function NewShowSection() {
  const navigate = useNavigate()
  const drafts = useShowDraft()
  const { preferences, update, saveError } = usePodcastPreferences()
  const open = (made: SetupDraft | null) => {
    if (made) navigate('/podcasts/setup', { state: made })
  }
  return (
    <section aria-labelledby="new-show-heading" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
      <h2 id="new-show-heading" style={{ margin: 0, fontSize: 'var(--text-lg)', color: 'var(--color-text)' }}>Make your own show</h2>
      <ShowGenerator onGenerate={(idea) => void drafts.generate(idea).then(open)} onSurprise={() => void drafts.surprise().then(open)} isPending={drafts.isPending} error={drafts.error} />
      <InterestsEditor interests={preferences?.interests ?? []} onSave={(interests) => update({ interests })} error={saveError} />
    </section>
  )
}
