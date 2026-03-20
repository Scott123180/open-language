import { useState, useRef } from 'react'
import * as api from '../../services/api'

interface ExpressionHelperPanelProps {
  targetLanguage: string
  nativeLanguage: string
  onClose: () => void
}

interface HelperMessage {
  role: 'user' | 'assistant'
  content: string
  isStreaming?: boolean
}

export default function ExpressionHelperPanel({
  targetLanguage,
  nativeLanguage,
  onClose,
}: ExpressionHelperPanelProps) {
  const [messages, setMessages] = useState<HelperMessage[]>([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const helperSessionId = useRef(Math.random().toString(36).slice(2))

  const handleSend = async () => {
    const text = input.trim()
    if (!text || isStreaming) return

    setInput('')
    setIsStreaming(true)
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: text },
      { role: 'assistant', content: '', isStreaming: true },
    ])

    await api.streamHelper(
      text,
      helperSessionId.current,
      targetLanguage,
      nativeLanguage,
      (token) => {
        setMessages((prev) => {
          const msgs = [...prev]
          const last = msgs[msgs.length - 1]
          if (last?.role === 'assistant' && last.isStreaming) {
            msgs[msgs.length - 1] = { ...last, content: last.content + token }
          }
          return msgs
        })
      },
      () => {
        setMessages((prev) => {
          const msgs = [...prev]
          const last = msgs[msgs.length - 1]
          if (last?.role === 'assistant' && last.isStreaming) {
            msgs[msgs.length - 1] = { ...last, isStreaming: false }
          }
          return msgs
        })
        setIsStreaming(false)
      },
      (errMsg) => {
        setMessages((prev) => {
          const msgs = [...prev]
          const last = msgs[msgs.length - 1]
          if (last?.role === 'assistant') {
            msgs[msgs.length - 1] = { ...last, content: `Error: ${errMsg}`, isStreaming: false }
          }
          return msgs
        })
        setIsStreaming(false)
      },
    )
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div
      style={{
        borderTop: '2px solid var(--color-primary)',
        background: 'var(--color-bg)',
        display: 'flex',
        flexDirection: 'column',
        maxHeight: '280px',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '6px 16px',
          borderBottom: '1px solid var(--color-border)',
          background: 'var(--color-surface)',
        }}
      >
        <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--color-primary)' }}>
          🗣️ Expression Helper
          <span style={{ fontSize: '0.72rem', fontWeight: 400, fontStyle: 'italic', marginLeft: '6px', color: 'var(--color-text-muted)' }}>
            {nativeLanguage} → {targetLanguage}
          </span>
        </span>
        <button
          onClick={onClose}
          aria-label="Close Expression Helper"
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            fontSize: '1rem',
            color: 'var(--color-text-muted)',
            lineHeight: 1,
          }}
        >
          ✕
        </button>
      </div>

      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '8px 16px',
          display: 'flex',
          flexDirection: 'column',
          gap: '6px',
        }}
      >
        {messages.map((msg, i) => (
          <div
            key={i}
            style={{
              alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: '85%',
              padding: '6px 10px',
              borderRadius: 'var(--radius)',
              background: msg.role === 'user' ? 'var(--color-primary)' : 'var(--color-bg)',
              color: msg.role === 'user' ? '#fff' : 'var(--color-text)',
              border: msg.role === 'assistant' ? '1px solid var(--color-border)' : 'none',
              fontSize: '0.85rem',
            }}
          >
            {msg.content}
          </div>
        ))}
      </div>

      <div
        style={{
          display: 'flex',
          gap: '6px',
          padding: '8px 16px',
          borderTop: '1px solid var(--color-border)',
        }}
      >
        <input
          type="text"
          aria-label="Ask the expression helper"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isStreaming}
          placeholder={`Ask in ${nativeLanguage}…`}
          style={{
            flex: 1,
            padding: '7px 12px',
            borderRadius: 'var(--radius)',
            border: '1px solid var(--color-border)',
            fontSize: '0.85rem',
            background: isStreaming ? 'var(--color-bg)' : 'var(--color-surface)',
            color: 'var(--color-text)',
            outline: 'none',
          }}
        />
        <button
          onClick={handleSend}
          disabled={isStreaming || !input.trim()}
          aria-label="Ask expression helper"
          style={{
            padding: '7px 14px',
            background: 'transparent',
            color: isStreaming || !input.trim() ? 'var(--color-text-muted)' : 'var(--color-primary)',
            border: `1px solid ${isStreaming || !input.trim() ? 'var(--color-border)' : 'var(--color-primary)'}`,
            borderRadius: 'var(--radius)',
            fontSize: '0.85rem',
            fontWeight: 600,
            cursor: isStreaming || !input.trim() ? 'not-allowed' : 'pointer',
          }}
        >
          Ask →
        </button>
      </div>
    </div>
  )
}
