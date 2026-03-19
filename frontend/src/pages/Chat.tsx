import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import * as api from '../services/api'
import MessageBubble from '../components/chat/MessageBubble'
import RecordButton from '../components/chat/RecordButton'
import AudioPlayer from '../components/shared/AudioPlayer'
import ErrorBanner from '../components/shared/ErrorBanner'
import SuggestedResponsePanel from '../components/chat/SuggestedResponsePanel'
import ExpressionHelperPanel from '../components/chat/ExpressionHelperPanel'
import { useRecorder } from '../hooks/useRecorder'

interface LocalMessage {
  id?: number
  role: 'user' | 'assistant'
  content: string
  isStreaming?: boolean
}

export default function Chat() {
  const { conversationId } = useParams<{ conversationId: string }>()
  const navigate = useNavigate()
  const convId = Number(conversationId)

  const [messages, setMessages] = useState<LocalMessage[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [audioState, setAudioState] = useState<{ src: string; rate: number } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [textInput, setTextInput] = useState('')
  const [isProcessingVoice, setIsProcessingVoice] = useState(false)
  const [openingDone, setOpeningDone] = useState(false)
  const [targetLanguage, setTargetLanguage] = useState('Spanish')
  const [nativeLanguage, setNativeLanguage] = useState('English')
  const [scenarioTitle, setScenarioTitle] = useState('')
  const abortRef = useRef<AbortController | null>(null)

  const { startRecording, stopRecording, isRecording, error: recorderError } = useRecorder()
  const [micDenied, setMicDenied] = useState(false)

  // Load settings and conversation metadata
  useEffect(() => {
    api.getSettings().then((settings) => {
      setTargetLanguage(settings.target_language)
      setNativeLanguage(settings.native_language)
    }).catch(() => {
      // keep defaults
    })
    api.getConversation(convId).then((conv) => {
      setScenarioTitle(conv.scenario_title)
    }).catch(() => {
      // keep empty
    })
  }, [convId])

  // Detect microphone permission denied
  useEffect(() => {
    if (recorderError && (recorderError.includes('denied') || recorderError.includes('NotAllowed'))) {
      setMicDenied(true)
    }
  }, [recorderError])

  // Opening message stream
  useEffect(() => {
    const controller = new AbortController()
    abortRef.current = controller

    setIsStreaming(true)
    setMessages([{ role: 'assistant', content: '', isStreaming: true }])

    api.streamChatOpen(
      convId,
      (token) => {
        if (controller.signal.aborted) return
        setMessages((prev) => {
          const msgs = [...prev]
          const last = msgs[msgs.length - 1]
          if (last?.role === 'assistant') {
            msgs[msgs.length - 1] = { ...last, content: last.content + token }
          }
          return msgs
        })
      },
      (data) => {
        if (controller.signal.aborted) return
        setMessages((prev) => {
          const msgs = [...prev]
          const last = msgs[msgs.length - 1]
          if (last?.role === 'assistant') {
            msgs[msgs.length - 1] = { ...last, id: data.message_id, isStreaming: false }
          }
          return msgs
        })
        setIsStreaming(false)
        setOpeningDone(true)
        setAudioState({ src: `/api/audio/tts/${data.message_id}`, rate: 1.0 })
      },
      (errMsg) => {
        if (controller.signal.aborted) return
        setError(errMsg)
        setIsStreaming(false)
        setOpeningDone(true)
      },
    )

    return () => {
      controller.abort()
    }
  }, [convId])

  const handleEndChat = async () => {
    abortRef.current?.abort()
    try {
      await api.completeConversation(convId)
    } catch {
      // best-effort
    }
    navigate('/')
  }

  const appendUserMessage = (text: string, userMsgId: number) => {
    setMessages((prev) => [
      ...prev,
      { role: 'user', id: userMsgId, content: text },
      { role: 'assistant', content: '', isStreaming: true },
    ])
  }

  const appendToken = (token: string) => {
    setMessages((prev) => {
      const msgs = [...prev]
      const last = msgs[msgs.length - 1]
      if (last?.role === 'assistant' && last.isStreaming) {
        msgs[msgs.length - 1] = { ...last, content: last.content + token }
      }
      return msgs
    })
  }

  const finalizeAssistant = (messageId: number) => {
    setMessages((prev) => {
      const msgs = [...prev]
      const last = msgs[msgs.length - 1]
      if (last?.role === 'assistant' && last.isStreaming) {
        msgs[msgs.length - 1] = { ...last, id: messageId, isStreaming: false }
      }
      return msgs
    })
    setIsStreaming(false)
    setAudioState({ src: `/api/audio/tts/${messageId}`, rate: 1.0 })
  }

  const sendMessage = async (text: string, source: 'voice' | 'keyboard') => {
    if (!text.trim() || isStreaming) return
    setIsStreaming(true)

    await api.streamChatMessage(
      convId,
      text,
      source,
      (userMsgId) => appendUserMessage(text, userMsgId),
      (token) => appendToken(token),
      (data) => finalizeAssistant(data.message_id),
      (errMsg) => {
        setError(errMsg)
        setIsStreaming(false)
      },
    )
  }

  const handleTextSubmit = async () => {
    const text = textInput.trim()
    if (!text) return
    setTextInput('')
    await sendMessage(text, 'keyboard')
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleTextSubmit()
    }
  }

  const handleStartRecording = async () => {
    setError(null)
    await startRecording()
  }

  const handleStopRecording = async () => {
    setIsProcessingVoice(true)
    try {
      const blob = await stopRecording()
      const { text } = await api.transcribeAudio(blob)
      if (text.trim()) {
        await sendMessage(text.trim(), 'voice')
      } else {
        setError('Could not understand audio. Please try again.')
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Voice transcription failed')
    } finally {
      setIsProcessingVoice(false)
    }
  }

  const playSlower = (msgId: number) => {
    setAudioState({ src: `/api/audio/tts/${msgId}`, rate: 0.65 })
  }

  const listEndRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    listEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const inputDisabled = isStreaming || isProcessingVoice || isRecording

  return (
    <main
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        background: 'var(--color-bg)',
      }}
    >
      <header
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '12px 16px',
          borderBottom: '1px solid var(--color-border)',
          background: 'var(--color-surface)',
        }}
      >
        <div>
          <h1 style={{ fontSize: '1.1rem', fontWeight: 600, margin: 0 }}>Chat</h1>
          {scenarioTitle && (
            <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', margin: 0 }}>
              {scenarioTitle}
            </p>
          )}
        </div>
        <button
          onClick={handleEndChat}
          style={{
            padding: '8px 16px',
            background: 'var(--color-error)',
            color: '#fff',
            borderRadius: 'var(--radius)',
          }}
        >
          End Chat
        </button>
      </header>

      {error && (
        <div style={{ padding: '8px 16px' }}>
          <ErrorBanner message={error} onDismiss={() => setError(null)} />
        </div>
      )}

      <section
        aria-label='Chat messages'
        style={{ flex: 1, overflowY: 'auto', padding: '16px' }}
      >
        {messages.map((msg, i) => (
          <MessageBubble
            key={i}
            role={msg.role}
            content={msg.content}
            messageId={msg.id}
            isStreaming={msg.isStreaming}
            showLearningTools={msg.id != null && !msg.isStreaming}
            targetLanguage={targetLanguage}
            nativeLanguage={nativeLanguage}
            onPlaySlower={
              msg.role === 'assistant' && msg.id != null
                ? () => playSlower(msg.id as number)
                : undefined
            }
          />
        ))}
        {isStreaming && messages.length === 0 && (
          <p aria-live='polite' style={{ color: 'var(--color-text-muted)' }}>
            Connecting…
          </p>
        )}
        <div ref={listEndRef} />
      </section>

      <SuggestedResponsePanel conversationId={convId} isDisabled={isStreaming} />

      <ExpressionHelperPanel targetLanguage={targetLanguage} nativeLanguage={nativeLanguage} />

      {openingDone && (
        <footer
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '10px 16px',
            borderTop: '1px solid var(--color-border)',
            background: 'var(--color-surface)',
          }}
        >
          {micDenied ? (
            <p
              style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)', flexShrink: 0, maxWidth: '200px' }}
              aria-live='polite'
            >
              Microphone access was denied. You can still type your responses below.
            </p>
          ) : (
            <RecordButton
              isRecording={isRecording}
              isProcessing={isProcessingVoice}
              onStartRecording={handleStartRecording}
              onStopRecording={handleStopRecording}
            />
          )}
          <input
            type='text'
            aria-label='Type a message'
            value={textInput}
            onChange={(e) => setTextInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={inputDisabled}
            placeholder='Type a message…'
            style={{
              flex: 1,
              padding: '10px 14px',
              borderRadius: 'var(--radius)',
              border: '1px solid var(--color-border)',
              fontSize: '1rem',
              background: inputDisabled ? 'var(--color-bg)' : 'var(--color-surface)',
              color: 'var(--color-text)',
              outline: 'none',
            }}
          />
          <button
            onClick={handleTextSubmit}
            disabled={inputDisabled || !textInput.trim()}
            style={{
              padding: '10px 18px',
              background:
                inputDisabled || !textInput.trim()
                  ? 'var(--color-border)'
                  : 'var(--color-primary)',
              color: inputDisabled || !textInput.trim() ? 'var(--color-text-muted)' : '#fff',
              borderRadius: 'var(--radius)',
              fontWeight: 600,
              cursor: inputDisabled || !textInput.trim() ? 'not-allowed' : 'pointer',
            }}
          >
            Send
          </button>
        </footer>
      )}

      <AudioPlayer src={audioState?.src ?? null} autoPlay={true} playbackRate={audioState?.rate ?? 1.0} />
    </main>
  )
}
