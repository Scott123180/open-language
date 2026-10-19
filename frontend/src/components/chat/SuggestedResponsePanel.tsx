import { useEffect, useRef, useState } from 'react'
import * as api from '../../services/api'
import { IconLightbulb } from '../shared/icons'

type FetchSuggestions = (conversationId: number) => Promise<{ suggestions: string[] }>

interface SuggestedResponsePanelProps {
  conversationId: number
  isDisabled?: boolean
  /** The newest message: suggestions are for it, and are asked for again once it changes. */
  lastMessageId?: number
  /** Where the suggestions come from: the chat endpoint unless a screen supplies its own. */
  fetchSuggestions?: FetchSuggestions
}

const NOT_REQUESTED = Symbol('not requested')
type RequestKey = number | undefined | typeof NOT_REQUESTED

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

const panelStyle: React.CSSProperties = {
  padding: '8px 16px',
  borderTop: '1px solid var(--color-border)',
  background: 'var(--color-surface)',
}

const itemStyle: React.CSSProperties = {
  padding: '6px 10px',
  background: 'var(--color-bg)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius)',
  fontSize: '0.85rem',
  color: 'var(--color-text-muted)',
  fontStyle: 'italic',
}

export default function SuggestedResponsePanel({
  conversationId,
  isDisabled = false,
  lastMessageId,
  fetchSuggestions = api.getSuggestions,
}: SuggestedResponsePanelProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const shown = useSuggestions({ conversationId, lastMessageId, isActive: isExpanded && !isDisabled, fetchSuggestions })
  return (
    <div style={panelStyle}>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      {isExpanded ? (
        <ExpandedSuggestions shown={shown} onCollapse={() => setIsExpanded(false)} />
      ) : (
        <ExpandButton isDisabled={isDisabled} onExpand={() => setIsExpanded(true)} />
      )}
    </div>
  )
}

interface SuggestionsRequest {
  conversationId: number
  lastMessageId: number | undefined
  isActive: boolean
  fetchSuggestions: FetchSuggestions
}

interface ShownSuggestions {
  suggestions: string[]
  isLoading: boolean
}

/** Asks once per newest message, only while the panel is open and no reply is on its way. */
function useSuggestions({ conversationId, lastMessageId, isActive, fetchSuggestions }: SuggestionsRequest): ShownSuggestions {
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [loadedFor, setLoadedFor] = useState<RequestKey>(NOT_REQUESTED)
  const requestedFor = useRef<RequestKey>(NOT_REQUESTED)
  useEffect(() => {
    if (!isActive || requestedFor.current === lastMessageId) return
    requestedFor.current = lastMessageId
    const settle = (next: string[]) => {
      if (requestedFor.current !== lastMessageId) return
      setSuggestions(next)
      setLoadedFor(lastMessageId)
    }
    fetchSuggestions(conversationId)
      .then((data) => settle(data.suggestions))
      .catch(() => {
        settle([])
        requestedFor.current = NOT_REQUESTED
      })
  }, [isActive, lastMessageId, conversationId, fetchSuggestions])
  return { suggestions, isLoading: loadedFor !== lastMessageId }
}

function ExpandButton({ isDisabled, onExpand }: { isDisabled: boolean; onExpand: () => void }) {
  return (
    <button
      onClick={onExpand}
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
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
      }}
    >
      <IconLightbulb size={13} />
      Suggestions
    </button>
  )
}

function ExpandedSuggestions({ shown, onCollapse }: { shown: ShownSuggestions; onCollapse: () => void }) {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--color-text-muted)', display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
          <IconLightbulb size={13} />
          Suggestions <span style={{ fontSize: '0.75rem', fontStyle: 'italic', fontWeight: 400 }}>(read only)</span>
        </span>
        <button
          onClick={onCollapse}
          aria-label="Collapse suggestions"
          style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '0.8rem', color: 'var(--color-text-muted)' }}
        >
          ▲ collapse
        </button>
      </div>
      {shown.isLoading ? <span role="status" style={spinnerStyle} /> : <SuggestionList suggestions={shown.suggestions} />}
    </div>
  )
}

function SuggestionList({ suggestions }: { suggestions: string[] }) {
  return (
    <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '6px' }}>
      {suggestions.map((suggestion, index) => (
        <li key={index} style={itemStyle}>
          {suggestion}
        </li>
      ))}
    </ul>
  )
}
