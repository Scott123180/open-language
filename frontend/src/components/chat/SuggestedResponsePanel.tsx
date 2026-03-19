import { useState } from 'react'
import * as api from '../../services/api'

interface SuggestedResponsePanelProps {
  conversationId: number
  isDisabled?: boolean
}

const spinnerStyle: React.CSSProperties = {
  display: 'inline-block',
  width: '14px',
  height: '14px',
  border: '2px solid var(--color-border)',
  borderTopColor: 'var(--color-primary)',
  borderRadius: '50%',
  animation: 'spin 0.6s linear infinite',
  verticalAlign: 'middle',
}

export default function SuggestedResponsePanel({
  conversationId,
  isDisabled = false,
}: SuggestedResponsePanelProps) {
  const [expanded, setExpanded] = useState(false)
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [fetched, setFetched] = useState(false)

  const handleExpand = async () => {
    setExpanded(true)
    if (fetched) return
    setIsLoading(true)
    try {
      const data = await api.getSuggestions(conversationId)
      setSuggestions(data.suggestions)
      setFetched(true)
    } catch {
      setSuggestions([])
    } finally {
      setIsLoading(false)
    }
  }

  const handleCollapse = () => {
    setExpanded(false)
  }

  return (
    <div
      style={{
        padding: '8px 16px',
        borderTop: '1px solid var(--color-border)',
        background: 'var(--color-surface)',
      }}
    >
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      {!expanded ? (
        <button
          onClick={handleExpand}
          disabled={isDisabled}
          aria-label="Show suggestions"
          style={{
            padding: '6px 14px',
            fontSize: '0.85rem',
            background: 'var(--color-bg)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius)',
            color: 'var(--color-text-muted)',
            cursor: isDisabled ? 'not-allowed' : 'pointer',
          }}
        >
          💡 Suggestions
        </button>
      ) : (
        <div>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '8px',
            }}
          >
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--color-text-muted)' }}>
              💡 Suggestions <span style={{ fontSize: '0.75rem', fontStyle: 'italic' }}>(read only)</span>
            </span>
            <button
              onClick={handleCollapse}
              aria-label="Collapse suggestions"
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                fontSize: '0.8rem',
                color: 'var(--color-text-muted)',
              }}
            >
              ▲ collapse
            </button>
          </div>

          {isLoading ? (
            <span role="status" style={spinnerStyle} />
          ) : (
            <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {suggestions.map((s, i) => (
                <li
                  key={i}
                  style={{
                    padding: '6px 10px',
                    background: 'var(--color-bg)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius)',
                    fontSize: '0.85rem',
                    color: 'var(--color-text-muted)',
                    fontStyle: 'italic',
                  }}
                >
                  {s}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
