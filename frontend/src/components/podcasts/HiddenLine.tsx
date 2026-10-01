import { mutedTextStyle, secondaryButtonStyle } from './styles'

interface HiddenLineProps {
  speakerName: string
  onReveal: () => void
  onReplay?: () => void
}

const hiddenStyle = {
  ...secondaryButtonStyle,
  display: 'block',
  width: '100%',
  maxWidth: '80%',
  textAlign: 'left' as const,
  background: 'var(--color-surface-raised)',
  borderRadius: 'var(--radius-lg)',
}

/** A Listen line whose words are hidden: tap to show them; replay works meanwhile (FR-043). */
export default function HiddenLine({ speakerName, onReveal, onReplay }: HiddenLineProps) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-3)' }}>
      <button type="button" aria-label={`Show ${speakerName}'s line`} onClick={onReveal} style={hiddenStyle}>
        <span style={mutedTextStyle}>Tap to show the words</span>
      </button>
      {onReplay && (
        <button type="button" aria-label={`Replay ${speakerName}'s line`} onClick={onReplay} style={secondaryButtonStyle}>▶</button>
      )}
    </div>
  )
}
