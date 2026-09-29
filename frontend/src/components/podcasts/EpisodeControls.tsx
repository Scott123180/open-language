import type { Ref } from 'react'
import type { Awaiting, Turn } from '../../services/podcastsApi'
import { primaryButtonStyle, secondaryButtonStyle } from './styles'

interface EpisodeControlsProps {
  turn: Turn
  awaiting: Awaiting
  isPending: boolean
  onContinue: () => void
  onEnd: () => void
  continueRef?: Ref<HTMLButtonElement>
}

/** Continue is the primary action at the hosts' turn; End episode is always secondary. */
export default function EpisodeControls(props: EpisodeControlsProps) {
  const { turn, awaiting, isPending, onContinue, onEnd, continueRef } = props
  if (turn === 'finished') return null
  const canContinue = turn === 'hosts' && awaiting === 'continue'
  return (
    <div style={{ display: 'flex', gap: 'var(--space-2)', justifyContent: 'flex-end', flexWrap: 'wrap' }}>
      <button type="button" onClick={onEnd} disabled={isPending} style={secondaryButtonStyle}>End episode</button>
      {canContinue && (
        <button type="button" ref={continueRef} onClick={onContinue} disabled={isPending} style={primaryButtonStyle}>Continue</button>
      )}
    </div>
  )
}
