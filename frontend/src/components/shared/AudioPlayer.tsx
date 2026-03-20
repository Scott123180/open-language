import { useEffect } from 'react'
import { useAudio } from '../../hooks/useAudio'

interface AudioPlayerProps {
  src: string | null
  autoPlay?: boolean
  playbackRate?: number
  onEnded?: () => void
}

export default function AudioPlayer({ src, autoPlay = false, playbackRate = 1, onEnded }: AudioPlayerProps) {
  const { play, stop, setPlaybackRate, setOnEnded } = useAudio()

  useEffect(() => {
    setOnEnded(onEnded ?? null)
  }, [onEnded, setOnEnded])

  useEffect(() => {
    setPlaybackRate(playbackRate)
  }, [playbackRate, setPlaybackRate])

  useEffect(() => {
    if (autoPlay && src) {
      play(src)
    } else if (!src) {
      stop()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [src, autoPlay])

  return null
}
