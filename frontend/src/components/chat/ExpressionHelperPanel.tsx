import { useState, useRef } from 'react'
import * as api from '../../services/api'

interface ExpressionHelperPanelProps {
  targetLanguage: string
  nativeLanguage: string
}

interface HelperMessage {
  role: 'user' | 'assistant'
  content: string
  isStreaming?: boolean
}

export default function ExpressionHelperPanel({
  targetLanguage,
  nativeLanguage,
}: ExpressionHelperPanelProps) {
  const [expanded, setExpanded] = useState(false)
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

  if (!expanded) {
    return (
      <div style={{ padding: '8px 16px', borderTop: '1px solid var(--color-border)', background: 'var(--color-surface)' }}>
        <button
          onClick={() => setExpanded(true)}
          aria-label="Open Expression Helper"
          style={{
            padding: '6px 14px',
            fontSize: '0.85rem',
            background: 'var(--color-bg)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius)',
            color: 'var(--color-text-muted)',
            cursor: 'pointer',
          }}
        >
          🗣️ Expression Helper
        </button>
      </div>
    )
  }

  return (
    <div
      style={{
        borderTop: '1px solid var(--color-border)',
        background: 'var(--color-surface)',
        display: 'flex',
        flexDirection: 'column',
        maxHeight: '320px',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '8px 16px',
          borderBottom: '1px solid var(--color-border)',
        }}
      >
        <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--color-text-muted)' }}>
          🗣️ Expression Helper
          <span style={{ fontSize: '0.72rem', fontStyle: 'italic', marginLeft: '6px' }}>
            ({nativeLanguage} → {targetLanguage})
          </span>
        </span>
        <button
          onClick={() => setExpanded(false)}
          aria-label="Collapse Expression Helper"
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            fontSize: '0.8rem',
            color: 'var(--color-text-muted)',
          }}
        >
          ▼ collapse
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
          aria-label="Send to helper"
          style={{
            padding: '7px 14px',
            background:
              isStreaming || !input.trim() ? 'var(--color-border)' : 'var(--color-primary)',
            color: isStreaming || !input.trim() ? 'var(--color-text-muted)' : '#fff',
            borderRadius: 'var(--radius)',
            fontSize: '0.85rem',
            fontWeight: 600,
            cursor: isStreaming || !input.trim() ? 'not-allowed' : 'pointer',
          }}
        >
          Send
        </button>
      </div>
    </div>
  )
}
