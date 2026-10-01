import type { ReactNode } from 'react'
import MessageBubble from '../chat/MessageBubble'
import type { EpisodeHost, EpisodeLine } from '../../services/podcastsApi'
import HiddenLine from './HiddenLine'

interface HostLineProps {
  line: EpisodeLine
  host: EpisodeHost | undefined
  conversationId: number
  isAudioPlaying?: boolean
  onReplay?: () => void
  onPlaySlower?: () => void
  children?: ReactNode
  /** Listen with Show text off: the words wait for a tap (FR-043). */
  isHidden?: boolean
  onReveal?: (messageId: number) => void
}

const speakerStyle = {
  display: 'block',
  margin: '0 0 var(--space-1)',
  fontSize: 'var(--text-xs)',
  fontWeight: 'var(--weight-semibold)' as never,
  color: 'var(--color-text)',
}

/** One host's line: their name above the ordinary message bubble and its learning tools. */
export default function HostLine({ line, host, conversationId, children, isHidden, onReveal, ...audio }: HostLineProps) {
  const name = host?.name ?? 'Host'
  return (
    <div>
      <span style={speakerStyle}>{name}</span>
      {isHidden ? (
        <HiddenLine speakerName={name} onReveal={() => onReveal?.(line.message_id)} onReplay={audio.onReplay} />
      ) : (
        <MessageBubble role="assistant" content={line.content} messageId={line.message_id} conversationId={conversationId} showLearningTools {...audio}>
          {children}
        </MessageBubble>
      )}
    </div>
  )
}
