import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import * as api from '../services/flashcardsApi'
import ErrorBanner from '../components/shared/ErrorBanner'

function pct(count: number, total: number): string {
  if (total === 0) return '0%'
  return `${Math.round((count / total) * 100)}%`
}

function formatDuration(seconds: number | null): string {
  if (seconds == null) return '—'
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return m > 0 ? `${m}m ${s}s` : `${s}s`
}

export default function FlashcardSummary() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()

  const { data: summary, isLoading, error } = useQuery({
    queryKey: ['session-summary', sessionId],
    queryFn: () => api.getSessionSummary(Number(sessionId)),
  })

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: '80px', color: 'var(--color-text-muted)' }}>
        Loading summary…
      </div>
    )
  }

  if (error || !summary) {
    return (
      <div style={{ padding: '24px' }}>
        <ErrorBanner message="Failed to load session summary." onDismiss={() => navigate('/flashcards/decks')} />
      </div>
    )
  }

  const total = summary.cards_reviewed

  return (
    <main
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        minHeight: '100vh',
        background: 'var(--color-bg)',
        padding: '40px 16px',
        gap: '24px',
      }}
    >
      <h1 style={{ fontSize: '1.5rem', fontWeight: 700, margin: 0 }}>Session Complete</h1>

      {/* Score breakdown */}
      <div
        style={{
          width: '100%',
          maxWidth: '480px',
          background: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius)',
          padding: '24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
        }}
      >
        <div style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', marginBottom: '4px' }}>
          {summary.cards_reviewed} of {summary.total_cards} cards reviewed
          {!summary.completed && ' (exited early)'}
        </div>

        {/* Visual bar */}
        <div style={{ height: '12px', borderRadius: '6px', overflow: 'hidden', display: 'flex', gap: '2px' }}>
          <div style={{ flex: summary.knew_it_count, background: '#22c55e', minWidth: summary.knew_it_count > 0 ? '4px' : 0 }} />
          <div style={{ flex: summary.guessed_count, background: '#f59e0b', minWidth: summary.guessed_count > 0 ? '4px' : 0 }} />
          <div style={{ flex: summary.didnt_know_count, background: '#ef4444', minWidth: summary.didnt_know_count > 0 ? '4px' : 0 }} />
        </div>

        <div style={{ display: 'flex', gap: '16px', justifyContent: 'space-around', fontSize: '0.9rem' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontWeight: 700, color: '#22c55e', fontSize: '1.25rem' }}>{summary.knew_it_count}</div>
            <div style={{ color: 'var(--color-text-muted)', fontSize: '0.8rem' }}>Knew It ({pct(summary.knew_it_count, total)})</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontWeight: 700, color: '#f59e0b', fontSize: '1.25rem' }}>{summary.guessed_count}</div>
            <div style={{ color: 'var(--color-text-muted)', fontSize: '0.8rem' }}>Guessed ({pct(summary.guessed_count, total)})</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontWeight: 700, color: '#ef4444', fontSize: '1.25rem' }}>{summary.didnt_know_count}</div>
            <div style={{ color: 'var(--color-text-muted)', fontSize: '0.8rem' }}>Didn't Know ({pct(summary.didnt_know_count, total)})</div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '16px', fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
          <span>Duration: {formatDuration(summary.duration_seconds)}</span>
          {summary.current_streak > 0 && (
            <span>🔥 {summary.current_streak}-day streak</span>
          )}
        </div>
      </div>

      {/* Words needing work */}
      {summary.words_needing_work.length > 0 && (
        <div style={{ width: '100%', maxWidth: '480px' }}>
          <h2 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '8px' }}>Words to Review</h2>
          <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {summary.words_needing_work.map((w) => (
              <li
                key={w.id}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  padding: '8px 12px',
                  background: 'var(--color-surface)',
                  border: '1px solid var(--color-border)',
                  borderRadius: 'var(--radius)',
                  fontSize: '0.9rem',
                }}
              >
                <span>{w.word}</span>
                <span style={{ color: 'var(--color-text-muted)' }}>{w.translation}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Actions */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', width: '100%', maxWidth: '480px' }}>
        <button
          onClick={() => navigate(`/flashcards/decks`)}
          style={{
            padding: '12px 24px',
            background: 'var(--color-primary)',
            border: 'none',
            borderRadius: 'var(--radius)',
            color: 'var(--color-text-on-primary)',
            fontWeight: 600,
            fontSize: '1rem',
            cursor: 'pointer',
          }}
        >
          Back to Decks
        </button>
        <button
          onClick={async () => {
            try {
              const deck = await api.createMissedDeck(Number(sessionId))
              const session = await api.startSession(deck.id)
              navigate(`/flashcards/practice/${session.id}?deck_id=${deck.id}`)
            } catch {
              // silently ignore — no missed words
            }
          }}
          style={{
            padding: '12px 24px',
            background: 'none',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius)',
            color: 'var(--color-text)',
            fontSize: '1rem',
            cursor: 'pointer',
          }}
        >
          Practice Missed Words
        </button>
        <button
          onClick={() => navigate(`/flashcards/decks`)}
          style={{
            padding: '12px 24px',
            background: 'none',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius)',
            color: 'var(--color-text)',
            fontSize: '1rem',
            cursor: 'pointer',
          }}
        >
          Practice Again
        </button>
        <button
          onClick={() => navigate('/flashcards')}
          style={{
            padding: '12px 24px',
            background: 'none',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius)',
            color: 'var(--color-text)',
            fontSize: '1rem',
            cursor: 'pointer',
          }}
        >
          Back to Word List
        </button>
      </div>
    </main>
  )
}
