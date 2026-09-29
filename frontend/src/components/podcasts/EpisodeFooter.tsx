import type { Ref } from 'react'
import type { PodcastEpisode } from '../../hooks/podcasts/usePodcastEpisode'
import EpisodeControls from './EpisodeControls'
import LearnerComposer from './LearnerComposer'

interface EpisodeFooterProps {
  state: PodcastEpisode
  continueRef: Ref<HTMLButtonElement>
}

/** The actions of the moment: Continue at the hosts' turn, the input bar at the learner's. */
export default function EpisodeFooter({ state, continueRef }: EpisodeFooterProps) {
  const isLearnersTurn = state.turn === 'learner' && state.episode !== null
  return (
    <>
      <div style={{ padding: 'var(--space-2) var(--space-4)' }}>
        <EpisodeControls turn={state.turn} awaiting={state.awaiting} isPending={state.isPending} onContinue={state.next} onEnd={state.end} continueRef={continueRef} />
      </div>
      {isLearnersTurn && state.episode && (
        <LearnerComposer episode={state.episode} isPending={state.isPending} isAwaitingRetry={state.isAwaitingRetry} onSend={state.send} />
      )}
    </>
  )
}
