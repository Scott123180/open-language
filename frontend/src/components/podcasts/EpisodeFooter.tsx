import type { Ref } from 'react'
import type { PodcastEpisode } from '../../hooks/podcasts/usePodcastEpisode'
import EpisodeControls from './EpisodeControls'
import LearnerComposer from './LearnerComposer'

interface EpisodeFooterProps {
  state: PodcastEpisode
  continueRef: Ref<HTMLButtonElement>
}

function ControlsRow({ state, continueRef }: EpisodeFooterProps) {
  return (
    <div style={{ padding: 'var(--space-2) var(--space-4)' }}>
      <EpisodeControls
        turn={state.turn}
        awaiting={state.awaiting}
        isPending={state.isPending}
        canJumpIn={state.canJumpIn && !state.isJumpingIn}
        canPass={state.canPass}
        onContinue={state.next}
        onEnd={state.end}
        onJumpIn={state.jumpIn}
        onPass={state.pass}
        continueRef={continueRef}
      />
    </div>
  )
}

/** The actions of the moment: Continue at the hosts' turn, the input bar at the learner's, and
 * after a Jump in (plan interpretation 9). */
export default function EpisodeFooter({ state, continueRef }: EpisodeFooterProps) {
  const isComposing = state.turn === 'learner' || state.isJumpingIn
  return (
    <>
      <ControlsRow state={state} continueRef={continueRef} />
      {isComposing && state.episode && (
        <LearnerComposer episode={state.episode} isPending={state.isPending} isAwaitingRetry={state.isAwaitingRetry} onSend={state.send} />
      )}
    </>
  )
}
