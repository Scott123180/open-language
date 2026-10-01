import { useEffect, useRef } from 'react'
import MessageBubble from '../chat/MessageBubble'
import FeedbackNote from '../chat/FeedbackNote'
import type { FeedbackNoteData } from '../../services/api'
import type { EpisodeHost, EpisodeLine } from '../../services/podcastsApi'
import type { EpisodeAudio } from '../../hooks/podcasts/useEpisodeAudio'
import HostLine from './HostLine'

interface EpisodeTranscriptProps {
  conversationId: number
  lines: EpisodeLine[]
  hosts: EpisodeHost[]
  notes: Record<number, FeedbackNoteData[]>
  audio: EpisodeAudio
  isHidden: (line: EpisodeLine) => boolean
  onReveal: (messageId: number) => void
}

function Notes({ notes }: { notes: FeedbackNoteData[] | undefined }) {
  return <>{notes?.map((note) => <FeedbackNote key={note.id} note={note} />)}</>
}

function TranscriptLine({ line, props }: { line: EpisodeLine; props: EpisodeTranscriptProps }) {
  const { conversationId, hosts, notes, audio } = props
  if (line.speaker === 'learner') {
    return (
      <MessageBubble role="user" content={line.content} messageId={line.message_id} conversationId={conversationId} showLearningTools>
        <Notes notes={notes[line.message_id]} />
      </MessageBubble>
    )
  }
  const voiced = audio.canSpeak(line)
  const host = hosts.find((candidate) => candidate.host_id === line.host_id)
  return (
    <HostLine line={line} host={host} conversationId={conversationId} isHidden={props.isHidden(line)} onReveal={props.onReveal} isAudioPlaying={audio.isPlaying} onReplay={voiced ? () => audio.play(line.message_id) : undefined} onPlaySlower={voiced ? () => audio.playSlower(line.message_id) : undefined} />
  )
}

/** Every line of the episode in order: hosts under their names, the learner as in chat. */
export default function EpisodeTranscript(props: EpisodeTranscriptProps) {
  const endRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    // A braced body: newer browsers return a promise from a smooth scroll, which React would
    // otherwise take for the effect's clean-up and crash the episode.
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [props.lines.length])
  return (
    <section aria-label="Episode lines" style={{ flex: 1, overflowY: 'auto', padding: 'var(--space-4)' }}>
      {props.lines.map((line) => (
        <TranscriptLine key={line.message_id} line={line} props={props} />
      ))}
      <div ref={endRef} />
    </section>
  )
}
