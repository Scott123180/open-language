import { useState, useRef, useEffect } from 'react'

export interface UseAudioResult {
  play: (src: string) => void
  stop: () => void
  setPlaybackRate: (rate: number) => void
  setOnEnded: (cb: (() => void) | null) => void
  isPlaying: boolean
  error: Error | null
}

export function useAudio(): UseAudioResult {
  const audioRef = useRef<HTMLAudioElement>(new Audio())
  const [isPlaying, setIsPlaying] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const rateRef = useRef(1)
  const onEndedRef = useRef<(() => void) | null>(null)

  useEffect(() => {
    const audio = audioRef.current

    const onPlay = () => setIsPlaying(true)
    const onEnded = () => { setIsPlaying(false); onEndedRef.current?.() }
    const onPause = () => setIsPlaying(false)
    const onError = () => {
      setIsPlaying(false)
      setError(new Error('Audio playback error'))
    }

    audio.addEventListener('play', onPlay)
    audio.addEventListener('ended', onEnded)
    audio.addEventListener('pause', onPause)
    audio.addEventListener('error', onError)

    return () => {
      audio.removeEventListener('play', onPlay)
      audio.removeEventListener('ended', onEnded)
      audio.removeEventListener('pause', onPause)
      audio.removeEventListener('error', onError)
      audio.pause()
    }
  }, [])

  const play = (src: string) => {
    const audio = audioRef.current
    audio.src = src
    audio.playbackRate = rateRef.current
    setError(null)
    audio.play().catch((e: Error) => setError(e))
  }

  const stop = () => {
    const audio = audioRef.current
    audio.pause()
    audio.currentTime = 0
  }

  const setPlaybackRate = (rate: number) => {
    rateRef.current = rate
    audioRef.current.playbackRate = rate
  }

  const setOnEnded = (cb: (() => void) | null) => {
    onEndedRef.current = cb
  }

  return { play, stop, setPlaybackRate, setOnEnded, isPlaying, error }
}
