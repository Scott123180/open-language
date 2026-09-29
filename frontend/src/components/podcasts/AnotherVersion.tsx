import { useShowDraft, type SetupDraft } from '../../hooks/podcasts/useShowDraft'
import { mutedTextStyle, secondaryButtonStyle } from './styles'

interface AnotherVersionProps {
  current: SetupDraft
  onMade: (next: SetupDraft) => void
}

/** Another take on the same idea, never one of the titles already seen (FR-021). */
export default function AnotherVersion({ current, onMade }: AnotherVersionProps) {
  const drafts = useShowDraft()
  const ask = async () => {
    const made = await drafts.anotherVersion(current)
    if (made) onMade(made)
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1)', alignItems: 'flex-start' }}>
      <button type="button" onClick={() => void ask()} disabled={drafts.isPending} style={secondaryButtonStyle}>Another version</button>
      {drafts.isPending && <p role="status" style={{ ...mutedTextStyle, margin: 0 }}>Creating another version…</p>}
      {drafts.error && <p role="alert" style={{ margin: 0, color: 'var(--color-error)' }}>{drafts.error}</p>}
    </div>
  )
}
