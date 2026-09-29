import type { ReactNode } from 'react'
import MessageBubble from '../chat/MessageBubble'
import type { EpisodeHost, EpisodeLine } from '../../services/podcastsApi'

interface HostLineProps {
  line: EpisodeLine
  host: EpisodeHost | undefined
  conversationId: number
  isAudioPlaying?: boolean
  onReplay?: () => void
  onPlaySlower?: () => void
  children?: ReactNode
}

const speakerStyle = {
  display: 'block',
  margin: '0 0 var(--space-1)',
  fontSize: 'var(--text-xs)',
  fontWeight: 'var(--weight-semibold)' as never,
  color: 'var(--color-text)',
}

/** One host's line: their name above the ordinary message bubble and its learning tools. */
export default function HostLine({ line, host, conversationId, children, ...audio }: HostLineProps) {
  return (
    <div>
      <span style={speakerStyle}>{host?.name ?? 'Host'}</span>
      <MessageBubble role="assistant" content={line.content} messageId={line.message_id} conversationId={conversationId} showLearningTools {...audio}>
        {children}
      </MessageBubble>
    </div>
  )
}
