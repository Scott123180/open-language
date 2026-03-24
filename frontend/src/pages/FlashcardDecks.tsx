import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as api from '../services/flashcardsApi'
import ErrorBanner from '../components/shared/ErrorBanner'
import DeckConfigPanel from '../components/flashcards/DeckConfigPanel'
import { IconArrowLeft } from '../components/shared/icons'

const MODE_LABELS: Record<string, string> = {
  recall: 'Recall',
  listen: 'Listen',
  produce: 'Produce',
  fill_blank: 'Fill-in-the-Blank',
}

const ALGO_LABELS: Record<string, string> = {
  not_practiced: 'Not Practiced',
  difficult: 'Difficult',
  previously_guessed: 'Previously Guessed',
  mixed_review: 'Mixed Review',
}

export default function FlashcardDecks() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)

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
    <main
      style={{
        display: 'flex',
        flexDirection: 'column',
        minHeight: '100vh',
        background: 'var(--color-bg)',
      }}
    >
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
            borderRadius: 'var(--radius)',
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
        <div style={{ padding: '16px 24px', borderBottom: '1px solid var(--color-border)' }}>
          <DeckConfigPanel
            onCreated={(_deck) => {
              setShowCreate(false)
              queryClient.invalidateQueries({ queryKey: ['flashcard-decks'] })
              navigate(`/flashcards/decks`)
            }}
            onCancel={() => setShowCreate(false)}
          />
        </div>
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
          {decks.map((deck) => (
            <li
              key={deck.id}
              style={{
                background: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius)',
                padding: '16px 20px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                gap: '16px',
                flexWrap: 'wrap',
              }}
            >
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 600, fontSize: '1rem', marginBottom: '4px' }}>
                  {deck.name}
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                  <span>{deck.card_count} cards</span>
                  <span>{MODE_LABELS[deck.practice_mode] ?? deck.practice_mode}</span>
                  <span>{ALGO_LABELS[deck.algorithm] ?? deck.algorithm}</span>
                  {deck.last_practiced_at && (
                    <span>Last: {new Date(deck.last_practiced_at).toLocaleDateString()}</span>
                  )}
                  {deck.last_accuracy != null && (
                    <span>{Math.round(deck.last_accuracy * 100)}% accuracy</span>
                  )}
                </div>
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  aria-label={`Start practice for ${deck.name}`}
                  onClick={() => startMutation.mutate(deck.id)}
                  disabled={startMutation.isPending}
                  style={{
                    padding: '8px 16px',
                    background: 'var(--color-primary)',
                    border: 'none',
                    borderRadius: 'var(--radius)',
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
                    borderRadius: 'var(--radius)',
                    color: 'var(--color-text-muted)',
                    cursor: 'pointer',
                    fontSize: '0.85rem',
                  }}
                >
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </main>
  )
}
