import type { HostDraft } from '../../services/podcastsApi'
import { mutedTextStyle } from './styles'

interface HostCardProps {
  host: HostDraft
  personalityLabel: string
}

const hostCardStyle = {
  display: 'flex',
  flexDirection: 'column' as const,
  gap: 'var(--space-1)',
  padding: 'var(--space-3) var(--space-4)',
  background: 'var(--color-surface)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-lg)',
}

/** A host as the setup screen shows them: name and personality. */
export default function HostCard({ host, personalityLabel }: HostCardProps) {
  return (
    <div style={hostCardStyle}>
      <span style={{ fontWeight: 'var(--weight-semibold)' as never, color: 'var(--color-text)' }}>{host.name}</span>
      <span style={mutedTextStyle}>{personalityLabel}</span>
    </div>
  )
}
