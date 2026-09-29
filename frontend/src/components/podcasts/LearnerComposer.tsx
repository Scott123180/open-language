import { useState } from 'react'
import ErrorBanner from '../shared/ErrorBanner'
import SuggestedResponsePanel from '../chat/SuggestedResponsePanel'
import ExpressionHelperPanel from '../chat/ExpressionHelperPanel'
import { getEpisodeSuggestions } from '../../services/podcastsApi'
import type { Episode } from '../../services/podcastsApi'
import { useLearnerInput } from '../../hooks/podcasts/useLearnerInput'
import ComposerBar from './ComposerBar'

interface LearnerComposerProps {
  episode: Episode
  isPending: boolean
  isAwaitingRetry: boolean
  onSend: (text: string, source: 'voice' | 'keyboard', confidence?: number) => void
}

/** At the learner's turn: suggestions, the expression helper and the input bar (FR-027). */
export default function LearnerComposer({ episode, isPending, isAwaitingRetry, onSend }: LearnerComposerProps) {
  const [isHelperOpen, setIsHelperOpen] = useState(false)
  const input = useLearnerInput(episode.language, onSend)
  const id = episode.conversation_id
  return (
    <footer style={{ borderTop: '1px solid var(--color-border)', background: 'var(--color-surface)' }}>
      <SuggestedResponsePanel conversationId={id} isDisabled={isPending} fetchSuggestions={getEpisodeSuggestions} />
      {isHelperOpen && <ExpressionHelperPanel conversationId={id} targetName={episode.language_name} nativeName={episode.native_language_name} onClose={() => setIsHelperOpen(false)} />}
      {input.error && <ErrorBanner message={input.error} onDismiss={input.clearError} />}
      <div style={{ padding: 'var(--space-3) var(--space-4)' }}>
        <ComposerBar input={input} isDisabled={isPending} isAwaitingRetry={isAwaitingRetry} isHelperOpen={isHelperOpen} onToggleHelper={() => setIsHelperOpen((open) => !open)} />
      </div>
    </footer>
  )
}
