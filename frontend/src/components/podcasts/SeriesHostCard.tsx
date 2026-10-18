import type { CSSProperties } from 'react'
import type { SeriesHostView } from '../../services/podcastsApi'
import { mutedTextStyle, secondaryButtonStyle } from './styles'

interface SeriesHostCardProps {
  host: SeriesHostView
  onPlaySample: () => void
  onRecast?: () => void
}

const cardStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  alignItems: 'center',
  gap: 'var(--space-2)',
  padding: 'var(--space-3) var(--space-4)',
  background: 'var(--color-surface)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-lg)',
}

const nameStyle: CSSProperties = { display: 'flex', flexDirection: 'column', flex: '1 1 8rem', color: 'var(--color-text)' }

/** A series host: the same person every episode, so read-only, with no Shuffle (FR-008).
 * Recast… is the deliberate way to replace them (FR-009). */
export default function SeriesHostCard({ host, onPlaySample, onRecast }: SeriesHostCardProps) {
  return (
    <div style={cardStyle}>
      <span style={nameStyle}>
        <span style={{ fontWeight: 'var(--weight-semibold)' as never }}>{host.name}</span>
        <span style={mutedTextStyle}>{host.personality_label}</span>
      </span>
      <button type="button" onClick={onPlaySample} disabled={!host.is_voice_available} aria-label={`Play ${host.name}'s voice`} style={secondaryButtonStyle}>▶</button>
      {onRecast && <button type="button" onClick={onRecast} aria-label={`Recast ${host.name}`} style={secondaryButtonStyle}>Recast…</button>}
      {host.voice_unavailable_message && <p style={{ ...mutedTextStyle, flexBasis: '100%', margin: 0 }}>{host.voice_unavailable_message}</p>}
    </div>
  )
}
