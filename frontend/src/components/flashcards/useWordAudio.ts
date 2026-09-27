import { useCallback, useState } from 'react'
import { describeAudioFailure } from '../../services/flashcardsApi'

export interface WordAudio {
  play: (rate: number) => Promise<void>
  /** Why the last play failed, or null. */
  failureMessage: string | null
}

/** Plays a word's audio; a failed play asks the server why (FR-018). */
export function useWordAudio(ttsUrl: string): WordAudio {
  const [failureMessage, setFailureMessage] = useState<string | null>(null)
  const play = useCallback(
    async (rate: number) => {
      const audio = new Audio(ttsUrl)
      audio.playbackRate = rate
      try {
        await audio.play()
        setFailureMessage(null)
      } catch {
        setFailureMessage(await describeAudioFailure(ttsUrl))
      }
    },
    [ttsUrl],
  )
  return { play, failureMessage }
}
