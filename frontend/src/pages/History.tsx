import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import * as api from '../services/api'
import type { Conversation, Message } from '../services/api'

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function History() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [messages, setMessages] = useState<Record<number, Message[]>>({})
  const [loadingMessages, setLoadingMessages] = useState<number | null>(null)

  useEffect(() => {
    api
      .getConversations()
      .then((data) => {
        setConversations(data)
        setIsLoading(false)
      })
      .catch(() => {
        setIsLoading(false)
      })
  }, [])

  const handleToggle = async (id: number) => {
    if (expandedId === id) {
      setExpandedId(null)
      return
    }
    setExpandedId(id)
    if (!messages[id]) {
      setLoadingMessages(id)
      try {
        const msgs = await api.getMessages(id)
        setMessages((prev) => ({ ...prev, [id]: msgs }))
      } finally {
        setLoadingMessages(null)
      }
    }
  }

  return (
    <main
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '40px 16px',
        gap: '24px',
        minHeight: '100vh',
        background: 'var(--color-bg)',
      }}
    >
      <h1 style={{ fontSize: '1.75rem', fontWeight: 700 }}>Past Chats</h1>
      <Link to='/' style={{ color: 'var(--color-primary)', alignSelf: 'flex-start' }}>
        ← Back to Home
      </Link>

      {isLoading && <p aria-live='polite'>Loading…</p>}

      {!isLoading && conversations.length === 0 && (
        <p style={{ color: 'var(--color-text-muted)' }}>No past conversations yet.</p>
      )}

      {!isLoading && conversations.length > 0 && (
        <ul
          style={{
            listStyle: 'none',
            padding: 0,
            margin: 0,
            width: '100%',
            maxWidth: '640px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
          }}
        >
          {conversations.map((conv) => (
            <li
              key={conv.id}
              style={{
                background: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius)',
                overflow: 'hidden',
              }}
            >
              <button
                onClick={() => handleToggle(conv.id)}
                aria-expanded={expandedId === conv.id}
                style={{
                  width: '100%',
                  textAlign: 'left',
                  padding: '16px',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '4px',
                  color: 'var(--color-text)',
                }}
              >
                <span style={{ fontWeight: 600 }}>{conv.scenario_title}</span>
                <span style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
                  {formatDate(conv.started_at)}
                </span>
                <span
                  style={{
                    fontSize: '0.75rem',
                    color: conv.status === 'completed' ? 'var(--color-success, green)' : 'var(--color-primary)',
                  }}
                >
                  {conv.status}
                </span>
              </button>

              {expandedId === conv.id && (
                <div
                  style={{
                    borderTop: '1px solid var(--color-border)',
                    padding: '12px 16px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '8px',
                  }}
                >
                  {loadingMessages === conv.id && (
                    <p aria-live='polite' style={{ color: 'var(--color-text-muted)', fontSize: '0.875rem' }}>
                      Loading messages…
                    </p>
                  )}
                  {messages[conv.id]?.map((msg) => (
                    <div
                      key={msg.id}
                      style={{
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '2px',
                        alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                        maxWidth: '80%',
                      }}
                    >
                      <span
                        style={{
                          fontSize: '0.75rem',
                          color: 'var(--color-text-muted)',
                          textAlign: msg.role === 'user' ? 'right' : 'left',
                        }}
                      >
                        {msg.role}
                      </span>
                      <span
                        style={{
                          padding: '8px 12px',
                          borderRadius: 'var(--radius)',
                          background: msg.role === 'user' ? 'var(--color-primary)' : 'var(--color-border)',
                          color: msg.role === 'user' ? '#fff' : 'var(--color-text)',
                          fontSize: '0.9rem',
                        }}
                      >
                        {msg.content}
                      </span>
                    </div>
                  ))}
                  {messages[conv.id]?.length === 0 && (
                    <p style={{ color: 'var(--color-text-muted)', fontSize: '0.875rem' }}>No messages.</p>
                  )}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </main>
  )
}
