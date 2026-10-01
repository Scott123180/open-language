import { useState } from 'react'
import * as api from '../../services/api'
import { useRecorder } from '../useRecorder'

type Send = (text: string, source: 'voice' | 'keyboard', confidence?: number) => void

const NOT_UNDERSTOOD = 'Could not understand audio. Please try again.'

export interface LearnerInput {
  text: string
  setText: (text: string) => void
  submit: () => void
  isRecording: boolean
  isTranscribing: boolean
  startRecording: () => Promise<void>
  stopRecording: () => Promise<void>
  error: string | null
  clearError: () => void
}

/** Typed or spoken input. Speech is transcribed in the episode's language (FR-029). */
export function useLearnerInput(language: string, onSend: Send): LearnerInput {
  const [text, setText] = useState('')
  const submit = () => {
    const trimmed = text.trim()
    if (!trimmed) return
    setText('')
    onSend(trimmed, 'keyboard')
  }
  return { text, setText, submit, ...useSpokenInput(language, onSend) }
}

function useSpokenInput(language: string, onSend: Send) {
  const [isTranscribing, setIsTranscribing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { isRecording, startRecording, stopRecording: stop } = useRecorder()
  const stopRecording = async () => {
    setIsTranscribing(true)
    try {
      await sendTranscription(await stop(), language, onSend)
    } catch (e) {
      setError(e instanceof Error ? e.message : NOT_UNDERSTOOD)
    } finally {
      setIsTranscribing(false)
    }
  }
  return { isRecording, isTranscribing, startRecording, stopRecording, error, clearError: () => setError(null) }
}

async function sendTranscription(blob: Blob, language: string, onSend: Send): Promise<void> {
  const { text, confidence } = await api.transcribeAudio(blob, language)
  if (!text.trim()) throw new Error(NOT_UNDERSTOOD)
  // 0.0 is a real confidence (hallucination-on-silence), so test for null.
  onSend(text.trim(), 'voice', confidence ?? undefined)
}
