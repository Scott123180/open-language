import ErrorBanner from '../shared/ErrorBanner'
import { secondaryButtonStyle } from './styles'

interface EpisodeErrorProps {
  message: string | null
  onRetry: () => void
}

/** A failed line, in the provider's plain words, with Retry for the same line (FR-033). */
export default function EpisodeError({ message, onRetry }: EpisodeErrorProps) {
  if (!message) return null
  return (
    <div role="alert" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', padding: 'var(--space-2) var(--space-4)' }}>
      <div style={{ flex: 1 }}>
        <ErrorBanner message={message} />
      </div>
      <button type="button" onClick={onRetry} style={secondaryButtonStyle}>Retry</button>
    </div>
  )
}
