import type { UnfinishedEpisode } from '../../services/podcastsApi'
import { primaryButtonStyle } from './styles'

interface ContinueEpisodeProps {
  unfinished: UnfinishedEpisode
  onContinue: (conversationId: number) => void
  onStartNew: () => void
  isStarting: boolean
}

const textButtonStyle = {
  alignSelf: 'flex-start',
  background: 'transparent',
  color: 'var(--color-text-muted)',
  textDecoration: 'underline',
  padding: '0 var(--space-1)',
}

/** An unfinished episode is offered first; a new one stays a secondary choice (research R4). */
export default function ContinueEpisode({ unfinished, onContinue, onStartNew, isStarting }: ContinueEpisodeProps) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
      <button type="button" onClick={() => onContinue(unfinished.conversation_id)} style={{ ...primaryButtonStyle, alignSelf: 'flex-start' }}>
        {`Continue episode ${unfinished.episode_number}`}
      </button>
      <button type="button" onClick={onStartNew} disabled={isStarting} style={textButtonStyle}>Start a new episode instead</button>
    </div>
  )
}
