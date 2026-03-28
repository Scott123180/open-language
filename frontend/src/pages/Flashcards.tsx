import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as api from '../services/flashcardsApi'
import type { WordFilters, WordSort, WordClassification, WordListItem as WordListItemType } from '../services/flashcardsApi'
import WordFilterBar from '../components/flashcards/WordFilterBar'
import WordListItem from '../components/flashcards/WordListItem'
import ErrorBanner from '../components/shared/ErrorBanner'
import { IconArrowLeft } from '../components/shared/icons'

const CLASSIFICATION_RANK: Record<WordClassification, number> = {
  difficult: 4,
  not_practiced: 3,
  almost_learned: 2,
  learned: 1,
}

function applySortOrder(words: WordListItemType[], sort: WordSort): WordListItemType[] {
  const copy = [...words]
  switch (sort) {
    case 'saved_at_desc': return copy.sort((a, b) => b.saved_at.localeCompare(a.saved_at))
    case 'saved_at_asc':  return copy.sort((a, b) => a.saved_at.localeCompare(b.saved_at))
    case 'word_asc':      return copy.sort((a, b) => a.word.localeCompare(b.word))
    case 'classification_desc':
      return copy.sort((a, b) => CLASSIFICATION_RANK[b.classification] - CLASSIFICATION_RANK[a.classification])
  }
}

export default function Flashcards() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [filters, setFilters] = useState<WordFilters>({})
  const [sort, setSort] = useState<WordSort>('saved_at_desc')
  const [isSelecting, setIsSelecting] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [showBulkConfirm, setShowBulkConfirm] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { data: words = [], isLoading } = useQuery({
    queryKey: ['flashcard-words', filters],
    queryFn: () => api.fetchWords(filters),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteWord(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['flashcard-words'] }),
    onError: (e: Error) => setError(e.message),
  })

  const bulkDeleteMutation = useMutation({
    mutationFn: (ids: number[]) => api.deleteWords(ids),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['flashcard-words'] })
      setSelectedIds(new Set())
      setIsSelecting(false)
      setShowBulkConfirm(false)
    },
    onError: (e: Error) => setError(e.message),
  })

  function toggleSelect(id: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function exitSelectMode() {
    setIsSelecting(false)
    setSelectedIds(new Set())
  }

  const sortedWords = applySortOrder(words, sort)

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

      <WordFilterBar
        filters={filters}
        onChange={setFilters}
        sort={sort}
        onSortChange={setSort}
        isSelecting={isSelecting}
        onToggleSelecting={() => isSelecting ? exitSelectMode() : setIsSelecting(true)}
        hasWords={words.length > 0}
      />

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

        {!isLoading && sortedWords.length > 0 && (
          <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
            {sortedWords.map((word) => (
              <li key={word.id}>
                <WordListItem
                  word={word}
                  onDelete={(id) => deleteMutation.mutate(id)}
                  isSelected={selectedIds.has(word.id)}
                  onToggleSelect={isSelecting ? toggleSelect : undefined}
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

      {/* Floating bulk-action bar */}
      {isSelecting && selectedIds.size > 0 && (
        <div
          style={{
            position: 'fixed',
            bottom: 0,
            left: 0,
            right: 0,
            background: 'var(--color-surface)',
            borderTop: '1px solid var(--color-border)',
            padding: 'var(--space-3) var(--space-4)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            boxShadow: 'var(--shadow-md)',
            zIndex: 10,
          }}
        >
          <span style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-sm)' }}>
            {selectedIds.size} word{selectedIds.size !== 1 ? 's' : ''} selected
          </span>
          <button
            onClick={() => setShowBulkConfirm(true)}
            style={{
              background: 'var(--color-error)',
              border: 'none',
              borderRadius: 'var(--radius-md)',
              color: 'var(--color-text-on-primary)',
              cursor: 'pointer',
              fontWeight: 600,
              padding: 'var(--space-2) var(--space-4)',
              fontSize: 'var(--text-sm)',
              minHeight: 'unset',
            }}
          >
            Delete {selectedIds.size} word{selectedIds.size !== 1 ? 's' : ''}
          </button>
        </div>
      )}

      {/* Bulk delete confirmation modal */}
      {showBulkConfirm && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="bulk-delete-title"
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 20,
          }}
          onClick={(e) => { if (e.target === e.currentTarget) setShowBulkConfirm(false) }}
        >
          <div
            style={{
              background: 'var(--color-surface)',
              borderRadius: 'var(--radius-lg)',
              padding: 'var(--space-6)',
              maxWidth: '320px',
              width: '100%',
              margin: 'var(--space-4)',
              boxShadow: 'var(--shadow-lg)',
            }}
          >
            <h2
              id="bulk-delete-title"
              style={{ margin: '0 0 var(--space-2)', fontSize: 'var(--text-md)', fontWeight: 700, color: 'var(--color-text)' }}
            >
              Delete {selectedIds.size} word{selectedIds.size !== 1 ? 's' : ''}?
            </h2>
            <p style={{ margin: '0 0 var(--space-4)', color: 'var(--color-text-muted)', fontSize: 'var(--text-sm)' }}>
              This cannot be undone.
            </p>
            <div style={{ display: 'flex', gap: 'var(--space-2)', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setShowBulkConfirm(false)}
                style={{
                  background: 'none',
                  border: '1px solid var(--color-border)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--color-text-muted)',
                  cursor: 'pointer',
                  padding: 'var(--space-2) var(--space-3)',
                  fontSize: 'var(--text-sm)',
                  minHeight: 'unset',
                }}
              >
                Cancel
              </button>
              <button
                onClick={() => bulkDeleteMutation.mutate([...selectedIds])}
                style={{
                  background: 'var(--color-error)',
                  border: 'none',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--color-text-on-primary)',
                  cursor: 'pointer',
                  fontWeight: 600,
                  padding: 'var(--space-2) var(--space-3)',
                  fontSize: 'var(--text-sm)',
                  minHeight: 'unset',
                }}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  )
}
