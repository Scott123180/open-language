import type { CSSProperties } from 'react'
import type { HostDraft } from '../../services/podcastsApi'
import { mutedTextStyle, secondaryButtonStyle } from './styles'

interface GuestCardProps {
  guest: HostDraft | null
  personalityLabel: string
  isCasting: boolean
  error: string | null
  onAnother: () => void
  /** Absent for the automatic expert, who leaves when the format goes back. */
  onRemove?: () => void
}

const cardStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  alignItems: 'center',
  gap: 'var(--space-2)',
  padding: 'var(--space-3) var(--space-4)',
  background: 'var(--color-surface)',
  border: '1px dashed var(--color-border)',
  borderRadius: 'var(--radius-lg)',
}

const nameStyle: CSSProperties = { display: 'flex', flexDirection: 'column', flex: '1 1 8rem', color: 'var(--color-text)' }

/** This episode's guest: never kept by the series (011 FR-020, FR-024a). */
export default function GuestCard({ guest, personalityLabel, isCasting, error, onAnother, onRemove }: GuestCardProps) {
  return (
    <div style={cardStyle} role="status" aria-busy={isCasting}>
      <span style={nameStyle}>
        <span style={mutedTextStyle}>Guest · this episode</span>
        <span style={{ fontWeight: 'var(--weight-semibold)' as never }}>{isCasting ? 'Casting…' : guest?.name ?? 'No guest'}</span>
        {guest && !isCasting && <span style={mutedTextStyle}>{personalityLabel}</span>}
      </span>
      {guest && <button type="button" onClick={onAnother} disabled={isCasting} style={secondaryButtonStyle}>Another guest</button>}
      {guest && onRemove && <button type="button" onClick={onRemove} style={secondaryButtonStyle}>Remove guest</button>}
      {error && <p role="alert" style={{ ...mutedTextStyle, flexBasis: '100%', margin: 0 }}>{error}</p>}
    </div>
  )
}
