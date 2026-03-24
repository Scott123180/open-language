import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as api from '../services/flashcardsApi'
import type { WordFilters, WordClassification } from '../services/flashcardsApi'
import WordFilterBar from '../components/flashcards/WordFilterBar'
import WordListItem from '../components/flashcards/WordListItem'
import ErrorBanner from '../components/shared/ErrorBanner'
import { IconArrowLeft } from '../components/shared/icons'

export default function Flashcards() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [filters, setFilters] = useState<WordFilters>({})
  const [error, setError] = useState<string | null>(null)

  const { data: words = [], isLoading } = useQuery({
    queryKey: ['flashcard-words', filters],
    queryFn: () => api.fetchWords(filters),
  })

  const classifyMutation = useMutation({
    mutationFn: ({ id, classification }: { id: number; classification: WordClassification }) =>
      api.updateClassification(id, classification),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['flashcard-words'] }),
    onError: (e: Error) => setError(e.message),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteWord(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['flashcard-words'] }),
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
          className="back-link"
          style={{ background: 'none', border: 'none', cursor: 'pointer' }}
        >
          <IconArrowLeft size={14} /> Home
        </button>
        <h1 style={{ fontSize: '1.05rem', fontWeight: 700, margin: 0, color: 'var(--color-text)' }}>My Words</h1>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <button
            onClick={() => navigate('/flashcards/analytics')}
            style={{
              background: 'none',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius)',
              color: 'var(--color-text-muted)',
              cursor: 'pointer',
              padding: '5px 12px',
              fontSize: '0.85rem',
              minHeight: 'unset',
            }}
          >
            Analytics
          </button>
          <button
            onClick={() => navigate('/flashcards/decks')}
            style={{
              background: 'none',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius)',
              color: 'var(--color-text-muted)',
              cursor: 'pointer',
              padding: '5px 12px',
              fontSize: '0.85rem',
              minHeight: 'unset',
            }}
          >
            My Decks
          </button>
          <button
            onClick={() => navigate('/flashcards/decks')}
            disabled={words.length === 0}
            style={{
              background: 'var(--color-primary)',
              border: 'none',
              borderRadius: 'var(--radius)',
              color: 'var(--color-text-on-primary)',
              cursor: words.length === 0 ? 'not-allowed' : 'pointer',
              fontWeight: 600,
              opacity: words.length === 0 ? 0.5 : 1,
              padding: '5px 14px',
              fontSize: '0.85rem',
              minHeight: 'unset',
            }}
          >
            Practice
          </button>
        </div>
      </header>

      {error && (
        <div style={{ padding: '0 24px', paddingTop: '12px' }}>
          <ErrorBanner message={error} onDismiss={() => setError(null)} />
        </div>
      )}

      <WordFilterBar filters={filters} onChange={setFilters} />

      <section style={{ flex: 1, overflowY: 'auto' }}>
        {isLoading && (
          <p
            aria-live="polite"
            style={{ textAlign: 'center', padding: '40px', color: 'var(--color-text-muted)' }}
          >
            Loading words…
          </p>
        )}

        {!isLoading && words.length === 0 && (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '8px',
              padding: '60px 24px',
              color: 'var(--color-text-muted)',
            }}
          >
            <p style={{ fontSize: '1rem', margin: 0 }}>No words found.</p>
            <p style={{ fontSize: '0.85rem', margin: 0 }}>
              Save words during a chat conversation to build your vocabulary list.
            </p>
          </div>
        )}

        {!isLoading && words.length > 0 && (
          <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
            {words.map((word) => (
              <li key={word.id}>
                <WordListItem
                  word={word}
                  onDelete={(id) => deleteMutation.mutate(id)}
                  onClassify={(id, classification) =>
                    classifyMutation.mutate({ id, classification })
                  }
                />
              </li>
            ))}
          </ul>
        )}
      </section>

      <footer
        style={{
          padding: '12px 24px',
          borderTop: '1px solid var(--color-border)',
          color: 'var(--color-text-muted)',
          fontSize: '0.8rem',
        }}
      >
        {words.length} word{words.length !== 1 ? 's' : ''}
      </footer>
    </main>
  )
}
