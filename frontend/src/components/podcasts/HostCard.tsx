import type { HostDraft, PersonalityOption } from '../../services/podcastsApi'
import ThemedSelect from '../shared/ThemedSelect'
import { secondaryButtonStyle } from './styles'

interface HostCardProps {
  host: HostDraft
  personalities: PersonalityOption[]
  /** The other host's personality, which this host may not take; null with one host. */
  otherPersonalityId: string | null
  isShuffling: boolean
  onShuffle: () => void
  onPersonalityChange: (personalityId: string) => void
  onPlaySample: () => void
}

const hostCardStyle = {
  display: 'flex',
  flexWrap: 'wrap' as const,
  alignItems: 'center',
  gap: 'var(--space-2)',
  padding: 'var(--space-3) var(--space-4)',
  background: 'var(--color-surface)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-lg)',
}

const selectStyle = { ...secondaryButtonStyle, width: 'auto', padding: '0 var(--space-3)', font: 'inherit', background: 'var(--color-surface)' }

/** A host on the setup screen: name, personality, a voice sample and Shuffle (US5). */
export default function HostCard({ host, personalities, otherPersonalityId, isShuffling, onShuffle, onPersonalityChange, onPlaySample }: HostCardProps) {
  const choices = personalities.filter((option) => option.personality_id !== otherPersonalityId)
  const selectId = `personality-${host.slot}`
  return (
    <div style={hostCardStyle}>
      <span style={{ fontWeight: 'var(--weight-semibold)' as never, color: 'var(--color-text)', flex: '1 1 6rem' }}>{host.name}</span>
      <ThemedSelect id={selectId} label={`${host.name}'s personality`} value={host.personality_id} onChange={onPersonalityChange}
        options={choices.map((option) => ({ value: option.personality_id, label: option.label }))} style={selectStyle} isCompact />
      <button type="button" onClick={onPlaySample} aria-label={`Play ${host.name}'s voice`} style={secondaryButtonStyle}>▶</button>
      <button type="button" onClick={onShuffle} disabled={isShuffling} aria-label={`Shuffle ${host.name}`} style={secondaryButtonStyle}>Shuffle</button>
    </div>
  )
}
