import type { EpisodeHost } from '../../services/podcastsApi'
import type { ArrivingLine as Arriving } from '../../hooks/podcasts/episodeState'
import { mutedTextStyle } from './styles'

interface ArrivingLineProps {
  arriving: Arriving
  host: EpisodeHost | undefined
  /** Listen with Show text off: the words stay hidden, like any line (FR-043). */
  isHidden: boolean
}

const speakerStyle = {
  display: 'block',
  margin: '0 0 var(--space-1)',
  fontSize: 'var(--text-xs)',
  fontWeight: 'var(--weight-semibold)' as never,
  color: 'var(--color-text)',
}

const bubbleStyle = {
  maxWidth: '80%',
  padding: 'var(--space-3) var(--space-4)',
  marginBottom: 'var(--space-3)',
  background: 'var(--color-surface-raised)',
  color: 'var(--color-text)',
  borderRadius: 'var(--radius-lg)',
  boxShadow: 'var(--shadow-sm)',
  lineHeight: 'var(--leading-relaxed)',
}

/** A host line still arriving, sentence by sentence; Replay and Slower come with the whole line. */
export default function ArrivingLine({ arriving, host, isHidden }: ArrivingLineProps) {
  const name = host?.name ?? 'Host'
  const words = arriving.parts.map((part) => part.text).join(' ')
  return (
    <div data-testid="arriving-line" aria-busy="true">
      <span style={speakerStyle}>{name}</span>
      {isHidden ? <span style={mutedTextStyle}>{name} is speaking…</span> : <div style={bubbleStyle}>{words}</div>}
    </div>
  )
}
