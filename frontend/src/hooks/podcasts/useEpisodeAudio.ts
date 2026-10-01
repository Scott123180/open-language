import { useCallback, useEffect, useRef, useState } from 'react'
import { getTtsUrl } from '../../services/api'
import type { EpisodeHost, EpisodeLine } from '../../services/podcastsApi'

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

/** Speaks each new host line in its host's voice as it arrives, never a line already on screen
 * when the episode opened, and never a line whose host has no voice (FR-029, FR-031). */
export function useEpisodeAudio(lines: EpisodeLine[], hosts: EpisodeHost[]): EpisodeAudio {
  const { source, isPlaying, setIsPlaying, speak } = useSpeaker()
  const canSpeak = useCallback(
    (line: EpisodeLine) => hosts.some((host) => host.host_id === line.host_id && host.is_voice_available),
    [hosts],
  )
  useNewLineSpeech(lines, hosts, canSpeak, speak)
  return {
    source,
    isPlaying,
    stopped: () => setIsPlaying(false),
    play: (id) => speak(id, NORMAL_RATE),
    playSlower: (id) => speak(id, SLOWER_RATE),
    canSpeak,
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

function useNewLineSpeech(
  lines: EpisodeLine[],
  hosts: EpisodeHost[],
  canSpeak: (line: EpisodeLine) => boolean,
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
    if (last?.speaker === 'host' && canSpeak(last)) speak(last.message_id, NORMAL_RATE)
  }, [lines.length, last, hosts.length, canSpeak, speak])
}
