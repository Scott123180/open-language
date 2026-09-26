import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import * as api from '../services/api'
import MessageBubble from '../components/chat/MessageBubble'
import RecordButton from '../components/chat/RecordButton'
import AudioPlayer from '../components/shared/AudioPlayer'
import ErrorBanner from '../components/shared/ErrorBanner'
import SuggestedResponsePanel from '../components/chat/SuggestedResponsePanel'
import ExpressionHelperPanel from '../components/chat/ExpressionHelperPanel'
import FeedbackNote from '../components/chat/FeedbackNote'
import TurnStatusIndicator from '../components/chat/TurnStatusIndicator'
import type { TurnStatus } from '../components/chat/TurnStatusIndicator'
import { IconMessageCircle } from '../components/shared/icons'
import { useRecorder } from '../hooks/useRecorder'

interface LocalMessage {
  id?: number
  role: 'user' | 'assistant'
  content: string
  isStreaming?: boolean
}

type NotesByMessage = Record<number, api.FeedbackNoteData[]>

function groupNotesByMessage(notes: api.FeedbackNoteData[]): NotesByMessage {
  return notes.reduce<NotesByMessage>((grouped, note) => {
    grouped[note.message_id] = [...(grouped[note.message_id] ?? []), note]
    return grouped
  }, {})
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
  const [helperExpanded, setHelperExpanded] = useState(false)
  const [isAudioPlaying, setIsAudioPlaying] = useState(false)
  const [targetLanguage, setTargetLanguage] = useState('Spanish')
  const [nativeLanguage, setNativeLanguage] = useState('English')
  const [scenarioTitle, setScenarioTitle] = useState('')
  const [notesByMessage, setNotesByMessage] = useState<NotesByMessage>({})
  const [awaitingRetry, setAwaitingRetry] = useState(false)
  const [correctionMode, setCorrectionMode] = useState<api.CorrectionMode>('off')
  const [turnStatus, setTurnStatus] = useState<TurnStatus>('idle')
  const abortRef = useRef<AbortController | null>(null)
  const loadStartedRef = useRef<number | null>(null)

  const { startRecording, stopRecording, isRecording, error: recorderError } = useRecorder()
  const [micDenied, setMicDenied] = useState(false)

  // Load settings and conversation metadata
  useEffect(() => {
    api.getSettings().then((settings) => {
      setTargetLanguage(settings.target_language)
      setNativeLanguage(settings.native_language)
      setCorrectionMode(settings.correction_mode)
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

  const streamOpening = (controller: AbortController) => {
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
  }

  const restoreTranscript = (existing: api.Message[]) => {
    setMessages(existing.map((m) => ({ id: m.id, role: m.role, content: m.content })))
    setIsStreaming(false)
    setOpeningDone(true)
  }

  const hydrateFeedback = async () => {
    try {
      const data = await api.getConversationFeedback(convId)
      setNotesByMessage(groupNotesByMessage(data.feedback))
      setAwaitingRetry(data.awaiting_retry)
    } catch {
      // Feedback is added context; a transcript without it is still usable.
    }
  }

  // A conversation that already has messages is resumed, never re-opened (R8).
  useEffect(() => {
    if (loadStartedRef.current === convId) return
    loadStartedRef.current = convId
    const controller = new AbortController()
    abortRef.current = controller
    setIsStreaming(true)

    const load = async () => {
      const existing = await api.getMessages(convId).catch(() => [] as api.Message[])
      if (controller.signal.aborted) return
      void hydrateFeedback()
      if (existing.length > 0) restoreTranscript(existing)
      else streamOpening(controller)
    }
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  // Off keeps today's send-time placeholder (SC-002). Gentle and Strict defer it
  // to the first token, so a flagged Strict turn never shows a phantom bubble (R11).
  const appendUserMessage = (text: string, userMsgId: number, deferReply: boolean) => {
    const appended: LocalMessage[] = [{ role: 'user', id: userMsgId, content: text }]
    if (!deferReply) appended.push({ role: 'assistant', content: '', isStreaming: true })
    setMessages((prev) => [...prev, ...appended])
  }

  const appendToken = (token: string) => {
    setTurnStatus('replying')
    setMessages((prev) => {
      const msgs = [...prev]
      const last = msgs[msgs.length - 1]
      if (last?.role === 'assistant' && last.isStreaming) {
        msgs[msgs.length - 1] = { ...last, content: last.content + token }
        return msgs
      }
      return [...msgs, { role: 'assistant', content: token, isStreaming: true }]
    })
  }

  const finalizeTurn = (messageId: number | null) => {
    setTurnStatus('idle')
    setIsStreaming(false)
    // A flagged Strict turn has no reply: no bubble to finalize, nothing to speak.
    if (messageId == null) return
    setMessages((prev) => {
      const msgs = [...prev]
      const last = msgs[msgs.length - 1]
      if (last?.role === 'assistant' && last.isStreaming) {
        msgs[msgs.length - 1] = { ...last, id: messageId, isStreaming: false }
      }
      return msgs
    })
    setAudioState({ src: `/api/audio/tts/${messageId}`, rate: 1.0 })
  }

  const attachFeedback = (data: api.FeedbackEventData) => {
    setNotesByMessage((prev) => ({ ...prev, [data.message_id]: data.notes }))
    if (data.awaiting_retry) setAwaitingRetry(true)
  }

  const sendMessage = async (
    text: string,
    source: 'voice' | 'keyboard',
    transcriptionConfidence?: number,
  ) => {
    if (!text.trim() || isStreaming) return
    const isCorrecting = correctionMode !== 'off'
    setIsStreaming(true)
    setAwaitingRetry(false)
    setTurnStatus(isCorrecting ? 'checking' : 'replying')

    await api.streamChatMessage(
      convId,
      text,
      source,
      (userMsgId) => appendUserMessage(text, userMsgId, isCorrecting),
      (token) => appendToken(token),
      (data) => finalizeTurn(data.message_id),
      (errMsg) => {
        setError(errMsg)
        setIsStreaming(false)
        setTurnStatus('idle')
      },
      attachFeedback,
      transcriptionConfidence,
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
      const { text, confidence } = await api.transcribeAudio(blob, targetLanguage || undefined)
      if (text.trim()) {
        // 0.0 is a real confidence (hallucination-on-silence), so test for null.
        await sendMessage(text.trim(), 'voice', confidence ?? undefined)
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
    setIsAudioPlaying(true)
    setAudioState(null)
    setTimeout(() => setAudioState({ src: `/api/audio/tts/${msgId}`, rate: 0.65 }), 0)
  }

  const playNormal = (msgId: number) => {
    setIsAudioPlaying(true)
    setAudioState(null)
    setTimeout(() => setAudioState({ src: `/api/audio/tts/${msgId}`, rate: 1.0 }), 0)
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
          display: 'grid',
          gridTemplateColumns: 'auto 1fr auto',
          alignItems: 'center',
          gap: '12px',
          padding: '0 16px',
          height: '52px',
          borderBottom: '1px solid var(--color-border)',
          background: 'var(--color-surface)',
        }}
      >
        <button
          onClick={() => navigate('/')}
          aria-label="Back to Home"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            background: 'none',
            border: 'none',
            color: 'var(--color-text-muted)',
            cursor: 'pointer',
            fontSize: '0.85rem',
            padding: '6px 8px',
            borderRadius: 'var(--radius-md)',
            minWidth: 'unset',
            minHeight: 'unset',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'var(--color-bg)'
            e.currentTarget.style.color = 'var(--color-text)'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'none'
            e.currentTarget.style.color = 'var(--color-text-muted)'
          }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <polyline points="15 18 9 12 15 6" />
          </svg>
          Home
        </button>
        <div>
          <h1 style={{ fontSize: '1.05rem', fontWeight: 600, margin: 0, color: 'var(--color-text)' }}>Chat</h1>
          {scenarioTitle && (
            <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', margin: 0, lineHeight: 1.2 }}>
              {scenarioTitle}
            </p>
          )}
        </div>
        <button
          onClick={handleEndChat}
          style={{
            padding: '5px 14px',
            background: 'var(--color-error)',
            color: 'var(--color-text-on-primary)',
            borderRadius: 'var(--radius-md)',
            fontSize: '0.85rem',
            minHeight: 'unset',
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
            conversationId={convId}
            isStreaming={msg.isStreaming}
            showLearningTools={msg.id != null && !msg.isStreaming}
            targetLanguage={targetLanguage}
            nativeLanguage={nativeLanguage}
            isAudioPlaying={isAudioPlaying}
            precedingMessage={i > 0 ? messages[i - 1].content : undefined}
            onReplay={
              msg.role === 'assistant' && msg.id != null
                ? () => playNormal(msg.id as number)
                : undefined
            }
            onPlaySlower={
              msg.role === 'assistant' && msg.id != null
                ? () => playSlower(msg.id as number)
                : undefined
            }
          >
            {(msg.id != null ? notesByMessage[msg.id] : undefined)?.map((note) => (
              <FeedbackNote key={note.id} note={note} />
            ))}
          </MessageBubble>
        ))}
        <TurnStatusIndicator status={turnStatus} />
        {isStreaming && messages.length === 0 && (
          <p aria-live='polite' style={{ color: 'var(--color-text-muted)' }}>
            Connecting…
          </p>
        )}
        <div ref={listEndRef} />
      </section>

      <SuggestedResponsePanel conversationId={convId} isDisabled={isStreaming} />

      {helperExpanded && (
        <ExpressionHelperPanel
          targetLanguage={targetLanguage}
          nativeLanguage={nativeLanguage}
          onClose={() => setHelperExpanded(false)}
        />
      )}

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
            placeholder={awaitingRetry ? 'Try again…' : 'Type a message…'}
            style={{
              flex: 1,
              padding: '10px 14px',
              borderRadius: 'var(--radius-md)',
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
            aria-label="Send message"
            style={{
              padding: '10px 18px',
              background:
                inputDisabled || !textInput.trim()
                  ? 'var(--color-border)'
                  : 'var(--color-primary)',
              color: inputDisabled || !textInput.trim() ? 'var(--color-text-muted)' : 'var(--color-text-on-primary)',
              borderRadius: 'var(--radius-md)',
              fontWeight: 600,
              cursor: inputDisabled || !textInput.trim() ? 'not-allowed' : 'pointer',
            }}
          >
            Send ↑
          </button>
          <button
            onClick={() => setHelperExpanded((v) => !v)}
            aria-label={helperExpanded ? 'Close expression helper' : 'Open expression helper'}
            title="Expression Helper"
            style={{
              padding: '0 12px',
              background: helperExpanded ? 'var(--color-primary)' : 'var(--color-bg)',
              color: helperExpanded ? 'var(--color-text-on-primary)' : 'var(--color-text-muted)',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-md)',
              cursor: 'pointer',
              flexShrink: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <IconMessageCircle size={18} />
          </button>
        </footer>
      )}

      <AudioPlayer
        src={audioState?.src ?? null}
        autoPlay={true}
        playbackRate={audioState?.rate ?? 1.0}
        onEnded={() => setIsAudioPlaying(false)}
      />
    </main>
  )
}
