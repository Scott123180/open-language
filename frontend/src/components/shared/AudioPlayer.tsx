import { useEffect } from 'react'
import { useAudio } from '../../hooks/useAudio'

interface AudioPlayerProps {
  src: string | null
  autoPlay?: boolean
  playbackRate?: number
}

export default function AudioPlayer({ src, autoPlay = false, playbackRate = 1 }: AudioPlayerProps) {
  const { play, stop, setPlaybackRate } = useAudio()

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
