import { useCallback, useEffect, useRef, useState } from 'react'
import { getTtsUrl } from '../../services/api'
import type { EpisodeHost, EpisodeLine } from '../../services/podcastsApi'
import type { StreamParts } from './episodeState'
import { usePartQueue } from './usePartQueue'
import type { PartQueue } from './usePartQueue'

const NORMAL_RATE = 1
const SLOWER_RATE = 0.65

export interface EpisodeAudio {
  source: { src: string; rate: number } | null
  isPlaying: boolean
  stopped: () => void
  play: (messageId: number) => void
  playSlower: (messageId: number) => void
  canSpeak: (line: EpisodeLine) => boolean
}

/** What the episode knows of lines streamed part by part (011 research R13). */
export interface StreamedSpeech {
  streamParts: StreamParts | null
  streamedIds: number[]
  lostStreamId: string | null
}

const NO_STREAM: StreamedSpeech = { streamParts: null, streamedIds: [], lostStreamId: null }

/** Speaks each new host line in its host's voice as it arrives: part by part when it streams,
 * never twice, never a line already on screen when the episode opened, and never a line whose
 * host has no voice (FR-029, FR-031). */
export function useEpisodeAudio(lines: EpisodeLine[], hosts: EpisodeHost[], stream = NO_STREAM): EpisodeAudio {
  const speaker = useSpeaker()
  const parts = usePartQueue()
  const canSpeak = useCallback(
    (line: EpisodeLine) => hosts.some((host) => host.host_id === line.host_id && host.is_voice_available),
    [hosts],
  )
  useArrivingParts(stream, parts)
  useNewLineSpeech(lines, hosts, (line) => canSpeak(line) && !stream.streamedIds.includes(line.message_id), speaker.speak)
  return { ...controls(speaker, parts), canSpeak }
}

/** Parts play first; Replay and Slower stop them and play the whole line. */
function controls(speaker: ReturnType<typeof useSpeaker>, parts: PartQueue) {
  const replay = (messageId: number, rate: number) => {
    parts.stop()
    speaker.speak(messageId, rate)
  }
  return {
    source: parts.current ? { src: parts.current, rate: NORMAL_RATE } : speaker.source,
    isPlaying: speaker.isPlaying || parts.current !== null,
    stopped: () => (parts.current ? parts.ended() : speaker.setIsPlaying(false)),
    play: (id: number) => replay(id, NORMAL_RATE),
    playSlower: (id: number) => replay(id, SLOWER_RATE),
  }
}

function useSpeaker() {
  const [source, setSource] = useState<EpisodeAudio['source']>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const speak = useCallback((messageId: number, rate: number) => {
    setIsPlaying(true)
    setSource(null)
    setTimeout(() => setSource({ src: getTtsUrl(messageId), rate }), 0)
  }, [])
  return { source, isPlaying, setIsPlaying, speak }
}

/** Queues each part of the latest streamed line once; a lost line's parts stop at once. */
function useArrivingParts(stream: StreamedSpeech, parts: PartQueue): void {
  const queuedRef = useRef({ streamId: null as string | null, count: 0 })
  const { streamParts, lostStreamId } = stream
  const { add, stop } = parts
  useEffect(() => {
    if (!streamParts) return
    const queued = queuedRef.current.streamId === streamParts.streamId ? queuedRef.current.count : 0
    streamParts.parts.slice(queued).forEach(add)
    queuedRef.current = { streamId: streamParts.streamId, count: streamParts.parts.length }
  }, [streamParts, add])
  useEffect(() => {
    if (lostStreamId) stop()
  }, [lostStreamId, stop])
}

function useNewLineSpeech(
  lines: EpisodeLine[],
  hosts: EpisodeHost[],
  shouldSpeak: (line: EpisodeLine) => boolean,
  speak: (messageId: number, rate: number) => void,
): void {
  const seenRef = useRef<number | null>(null)
  const last = lines[lines.length - 1]
  useEffect(() => {
    if (hosts.length === 0) return
    if (seenRef.current === null) {
      seenRef.current = lines.length
      return
    }
    if (lines.length === seenRef.current) return
    seenRef.current = lines.length
    if (last?.speaker === 'host' && shouldSpeak(last)) speak(last.message_id, NORMAL_RATE)
    // eslint-disable-next-line react-hooks/exhaustive-deps -- a new line, not a new predicate
  }, [lines.length, last, hosts.length, speak])
}
