import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as api from '../services/flashcardsApi'
import type { PracticeMode, GenerationAlgorithm } from '../services/flashcardsApi'
import ErrorBanner from '../components/shared/ErrorBanner'
import DeckConfigPanel from '../components/flashcards/DeckConfigPanel'
import {
  IconArrowLeft,
  IconEye, IconVolume, IconPenLine, IconTextCursor,
  IconShuffle, IconSparkles, IconFlame, IconTrophy,
} from '../components/shared/icons'

// ── Label & icon maps ────────────────────────────────────────────────────────

const MODE_LABELS: Record<PracticeMode, string> = {
  recall: 'Recall',
  listen: 'Listen',
  produce: 'Produce',
  fill_blank: 'Fill in the Blank',
}

const ALGO_LABELS: Record<GenerationAlgorithm, string> = {
  mixed_review: 'Mixed Review',
  not_practiced: 'New Words',
  difficult: 'Difficult',
  previously_guessed: 'Almost Learned',
}

const MODE_ICONS: Record<PracticeMode, React.ReactNode> = {
  recall: <IconEye size={20} />,
  listen: <IconVolume size={20} />,
  produce: <IconPenLine size={20} />,
  fill_blank: <IconTextCursor size={20} />,
}

const ALGO_ICONS: Record<GenerationAlgorithm, React.ReactNode> = {
  mixed_review: <IconShuffle size={20} />,
  not_practiced: <IconSparkles size={20} />,
  difficult: <IconFlame size={20} />,
  previously_guessed: <IconTrophy size={20} />,
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  const opts: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric' }
  if (date.getFullYear() !== new Date().getFullYear()) opts.year = 'numeric'
  return date.toLocaleDateString(undefined, opts)
}

function accuracyColor(accuracy: number): string {
  if (accuracy >= 0.8) return 'var(--color-success)'
  if (accuracy >= 0.6) return 'var(--color-warning)'
  return 'var(--color-error)'
}

// ── Component ────────────────────────────────────────────────────────────────

export default function FlashcardDecks() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)

  useEffect(() => {
    if (!showCreate) return
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') setShowCreate(false)
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [showCreate])

  const { data: decks = [], isLoading } = useQuery({
    queryKey: ['flashcard-decks'],
    queryFn: api.listDecks,
  })

  const deleteMutation = useMutation({
    mutationFn: api.deleteDeck,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['flashcard-decks'] }),
    onError: (e: Error) => setError(e.message),
  })

  const startMutation = useMutation({
    mutationFn: api.startSession,
    onSuccess: (session) => navigate(`/flashcards/practice/${session.id}?deck_id=${session.deck_id}`),
    onError: (e: Error) => setError(e.message),
  })

  return (
    <main style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', background: 'var(--color-bg)' }}>
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '16px 24px',
          borderBottom: '1px solid var(--color-border)',
          background: 'var(--color-surface)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <button
            onClick={() => navigate('/flashcards')}
            className="back-link"
            style={{ background: 'none', border: 'none', cursor: 'pointer' }}
          >
            <IconArrowLeft size={14} /> Words
          </button>
          <h1 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>My Decks</h1>
        </div>
        <button
          onClick={() => setShowCreate((v) => !v)}
          style={{
            background: 'var(--color-primary)',
            border: 'none',
            borderRadius: 'var(--radius-md)',
            color: 'var(--color-text-on-primary)',
            cursor: 'pointer',
            fontWeight: 600,
            padding: '8px 20px',
            fontSize: '0.9rem',
          }}
        >
          New Deck
        </button>
      </header>

      {error && (
        <div style={{ padding: '0 24px', paddingTop: '12px' }}>
          <ErrorBanner message={error} onDismiss={() => setError(null)} />
        </div>
      )}

      {showCreate && (
        <>
          <div
            aria-hidden="true"
            onClick={() => setShowCreate(false)}
            style={{
              position: 'fixed',
              inset: 0,
              background: 'rgba(28, 25, 23, 0.5)',
              backdropFilter: 'blur(4px)',
              zIndex: 40,
            }}
          />
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Create new deck"
            style={{
              position: 'fixed',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              width: 'min(480px, calc(100vw - 48px))',
              maxHeight: 'calc(100vh - 64px)',
              overflowY: 'auto',
              background: 'var(--color-surface)',
              borderRadius: 'var(--radius-xl)',
              boxShadow: 'var(--shadow-lg)',
              padding: '32px',
              zIndex: 50,
            }}
          >
            <button
              onClick={() => setShowCreate(false)}
              aria-label="Close"
              style={{
                position: 'absolute',
                top: '16px',
                right: '16px',
                background: 'none',
                border: 'none',
                color: 'var(--color-text-muted)',
                cursor: 'pointer',
                fontSize: '1.25rem',
                lineHeight: 1,
                padding: '4px 8px',
              }}
            >
              ×
            </button>
            <DeckConfigPanel
              onCreated={(_deck) => {
                setShowCreate(false)
                queryClient.invalidateQueries({ queryKey: ['flashcard-decks'] })
                navigate(`/flashcards/decks`)
              }}
              onCancel={() => setShowCreate(false)}
            />
          </div>
        </>
      )}

      <section style={{ flex: 1, padding: '16px 24px' }}>
        {isLoading && (
          <p aria-live="polite" style={{ color: 'var(--color-text-muted)' }}>
            Loading decks…
          </p>
        )}

        {!isLoading && decks.length === 0 && (
          <p style={{ color: 'var(--color-text-muted)', textAlign: 'center', paddingTop: '40px' }}>
            No decks yet. Create one to start practicing.
          </p>
        )}

        <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {decks.map((deck) => {
            const accuracy = deck.last_accuracy
            const isNew = deck.session_count === 0

            return (
              <li
                key={deck.id}
                style={{
                  background: 'var(--color-surface)',
                  border: '1px solid var(--color-border)',
                  borderRadius: 'var(--radius-lg)',
                  padding: '16px 20px',
                  display: 'flex',
                  gap: '16px',
                  alignItems: 'flex-start',
                  boxShadow: 'var(--shadow-sm)',
                }}
              >
                {/* Identity block — mode + algorithm icons */}
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '10px 8px',
                    background: 'var(--color-surface-raised)',
                    borderRadius: 'var(--radius-md)',
                    color: 'var(--color-primary)',
                    flexShrink: 0,
                  }}
                >
                  {MODE_ICONS[deck.practice_mode]}
                  {ALGO_ICONS[deck.algorithm]}
                </div>

                {/* Main content */}
                <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: '6px' }}>

                  {/* Title row */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                    <span style={{ fontWeight: 600, fontSize: '1rem', color: 'var(--color-text)' }}>
                      {MODE_LABELS[deck.practice_mode]} · {ALGO_LABELS[deck.algorithm]}
                    </span>
                    {isNew && (
                      <span style={{
                        fontSize: '0.7rem',
                        fontWeight: 600,
                        letterSpacing: '0.05em',
                        textTransform: 'uppercase',
                        background: 'var(--color-primary-subtle)',
                        color: 'var(--color-primary-text)',
                        borderRadius: '9999px',
                        padding: '2px 8px',
                      }}>
                        New
                      </span>
                    )}
                  </div>

                  {/* Subtitle */}
                  <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
                    {deck.card_count} cards
                    {deck.last_practiced_at
                      ? ` · ${formatDate(deck.last_practiced_at)}`
                      : ` · created ${formatDate(deck.created_at)}`}
                  </div>

                  {/* Accuracy bar */}
                  {accuracy != null && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '2px' }}>
                      <div style={{
                        flex: 1,
                        height: '4px',
                        background: 'var(--color-border)',
                        borderRadius: '9999px',
                        overflow: 'hidden',
                      }}>
                        <div style={{
                          height: '100%',
                          width: `${accuracy * 100}%`,
                          background: accuracyColor(accuracy),
                          borderRadius: '9999px',
                          transition: 'width 300ms ease',
                        }} />
                      </div>
                      <span style={{
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        color: accuracyColor(accuracy),
                        flexShrink: 0,
                      }}>
                        {Math.round(accuracy * 100)}%
                      </span>
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', flexShrink: 0 }}>
                  <button
                    aria-label={`Start practice for ${deck.name}`}
                    onClick={() => startMutation.mutate(deck.id)}
                    disabled={startMutation.isPending}
                    style={{
                      padding: '8px 16px',
                      background: 'var(--color-primary)',
                      border: 'none',
                      borderRadius: 'var(--radius-md)',
                      color: 'var(--color-text-on-primary)',
                      cursor: startMutation.isPending ? 'not-allowed' : 'pointer',
                      fontWeight: 600,
                      fontSize: '0.85rem',
                      opacity: startMutation.isPending ? 0.6 : 1,
                    }}
                  >
                    Practice
                  </button>
                  <button
                    aria-label={`Delete deck ${deck.name}`}
                    onClick={() => deleteMutation.mutate(deck.id)}
                    style={{
                      padding: '8px 12px',
                      background: 'none',
                      border: '1px solid var(--color-border)',
                      borderRadius: 'var(--radius-md)',
                      color: 'var(--color-text-muted)',
                      cursor: 'pointer',
                      fontSize: '0.85rem',
                    }}
                  >
                    Delete
                  </button>
                </div>
              </li>
            )
          })}
        </ul>
      </section>
    </main>
  )
}
