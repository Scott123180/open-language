import type { CSSProperties } from 'react'
import type { ConversationSummary, SummaryLanguage } from '../../services/api'
import { useConversationSummary } from '../../hooks/useConversationSummary'
import { useSummaryLanguage } from '../../hooks/useSummaryLanguage'

interface SummaryPanelProps {
  conversationId: number
  lastMessageId?: number
}

const panelStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 'var(--space-3)',
  padding: 'var(--space-4)',
  background: 'var(--color-surface)',
  color: 'var(--color-text)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-lg)',
  boxShadow: 'var(--shadow-md)',
  lineHeight: 'var(--leading-relaxed)',
}
const mutedStyle: CSSProperties = { margin: 0, color: 'var(--color-text-muted)', fontSize: 'var(--text-sm)' }
const buttonStyle: CSSProperties = {
  alignSelf: 'flex-start',
  minHeight: '44px',
  padding: '0 var(--space-4)',
  background: 'transparent',
  color: 'var(--color-text)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-md)',
}

/** A short summary of the conversation so far, in its language or in English (FR-035–FR-042). */
export default function SummaryPanel({ conversationId, lastMessageId }: SummaryPanelProps) {
  const { summary, error, isLoading, retry } = useConversationSummary(conversationId, true, lastMessageId)
  const [language, choose] = useSummaryLanguage()
  return (
    <section role="region" aria-label="Conversation summary" style={panelStyle}>
      {isLoading && <p aria-live="polite" style={mutedStyle}>Summarising…</p>}
      {error && <SummaryError message={error} onRetry={retry} />}
      {summary?.status === 'too_early' && <p style={mutedStyle}>{summary.message}</p>}
      {summary?.status === 'ready' && <ReadySummary summary={summary} language={language} onChoose={choose} />}
    </section>
  )
}

function SummaryError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div role="alert" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
      <p style={{ margin: 0, color: 'var(--color-error)' }}>{message}</p>
      <button type="button" onClick={onRetry} style={buttonStyle}>Retry</button>
    </div>
  )
}

type ReadyProps = {
  summary: Extract<ConversationSummary, { status: 'ready' }>
  language: SummaryLanguage
  onChoose: (language: SummaryLanguage) => void
}

function ReadySummary({ summary, language, onChoose }: ReadyProps) {
  const version = language === 'native' ? 'english' : 'conversation_language'
  return (
    <>
      <LanguageSwitch summary={summary} language={language} onChoose={onChoose} />
      <ul style={{ margin: 0, paddingLeft: 'var(--space-5)' }}>
        {summary.points.map((point, index) => (
          <li key={index}>{point[version]}</li>
        ))}
      </ul>
    </>
  )
}

function LanguageSwitch({ summary, language, onChoose }: ReadyProps) {
  const options: [SummaryLanguage, string][] = [
    ['conversation', summary.conversation_language_name],
    ['native', summary.native_language_name],
  ]
  return (
    <fieldset style={{ display: 'flex', gap: 'var(--space-4)', margin: 0, padding: 0, border: 'none' }}>
      <legend style={mutedStyle}>Summary language</legend>
      {options.map(([value, label]) => (
        <label key={value} style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1)', minHeight: '44px' }}>
          <input type="radio" name={`summary-language-${summary.conversation_id}`} checked={language === value} onChange={() => onChoose(value)} />
          {label}
        </label>
      ))}
    </fieldset>
  )
}
