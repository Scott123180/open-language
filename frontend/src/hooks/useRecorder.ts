import { useState, useRef } from 'react'

interface UseRecorderResult {
  startRecording: () => Promise<void>
  stopRecording: () => Promise<Blob>
  isRecording: boolean
  error: string | null
}

export function useRecorder(): UseRecorderResult {
  const [isRecording, setIsRecording] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const resolveRef = useRef<((blob: Blob) => void) | null>(null)
  const mimeTypeRef = useRef<string>('audio/webm')

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream

      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm'
      mimeTypeRef.current = mimeType

      const recorder = new MediaRecorder(stream, { mimeType })
      recorderRef.current = recorder
      chunksRef.current = []

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      recorder.start(100)
      setIsRecording(true)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Microphone access denied')
    }
  }

  const stopRecording = (): Promise<Blob> => {
    return new Promise((resolve) => {
      const recorder = recorderRef.current
      if (!recorder) {
        resolve(new Blob([], { type: 'audio/webm' }))
        return
      }

      resolveRef.current = resolve

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: mimeTypeRef.current })
        streamRef.current?.getTracks().forEach((t) => t.stop())
        setIsRecording(false)
        resolveRef.current?.(blob)
      }

      recorder.stop()
    })
  }

  return { startRecording, stopRecording, isRecording, error }
}
