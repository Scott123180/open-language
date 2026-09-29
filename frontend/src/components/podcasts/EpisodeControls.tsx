import type { Ref } from 'react'
import type { Awaiting, Turn } from '../../services/podcastsApi'
import { primaryButtonStyle, secondaryButtonStyle } from './styles'

interface EpisodeControlsProps {
  turn: Turn
  awaiting: Awaiting
  isPending: boolean
  canJumpIn: boolean
  canPass: boolean
  onContinue: () => void
  onEnd: () => void
  onJumpIn: () => void
  onPass: () => void
  continueRef?: Ref<HTMLButtonElement>
}

/** Continue is the primary action at the hosts' turn. End episode, and in a Panel Jump in and
 * Pass, are secondary (FR-017, Principle IV). */
export default function EpisodeControls(props: EpisodeControlsProps) {
  const { turn, awaiting, isPending } = props
  if (turn === 'finished') return null
  const canContinue = turn === 'hosts' && awaiting === 'continue'
  return (
    <div style={{ display: 'flex', gap: 'var(--space-2)', justifyContent: 'flex-end', flexWrap: 'wrap' }}>
      <button type="button" onClick={props.onEnd} disabled={isPending} style={secondaryButtonStyle}>End episode</button>
      {props.canPass && <button type="button" onClick={props.onPass} disabled={isPending} style={secondaryButtonStyle}>Pass</button>}
      {props.canJumpIn && <button type="button" onClick={props.onJumpIn} disabled={isPending} style={secondaryButtonStyle}>Jump in</button>}
      {canContinue && (
        <button type="button" ref={props.continueRef} onClick={props.onContinue} disabled={isPending} style={primaryButtonStyle}>Continue</button>
      )}
    </div>
  )
}
