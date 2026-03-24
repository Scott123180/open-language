import { useReducer, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import * as api from '../services/flashcardsApi'
import type { Rating } from '../services/flashcardsApi'
import CardPrompt from '../components/flashcards/CardPrompt'
import AudioControls from '../components/flashcards/AudioControls'
import CardAnswer from '../components/flashcards/CardAnswer'
import SelfAssessmentBar from '../components/flashcards/SelfAssessmentBar'
import ErrorBanner from '../components/shared/ErrorBanner'

// ---------------------------------------------------------------------------
// State machine
// ---------------------------------------------------------------------------

interface PracticeState {
  currentPosition: number
  isFlipped: boolean
  isSubmitting: boolean
  startTime: number
  error: string | null
}

type PracticeAction =
  | { type: 'FLIP' }
  | { type: 'SUBMIT_START' }
  | { type: 'SUBMIT_DONE'; nextPosition: number }
  | { type: 'ERROR'; message: string }
  | { type: 'DISMISS_ERROR' }

function reducer(state: PracticeState, action: PracticeAction): PracticeState {
  switch (action.type) {
    case 'FLIP':
      return { ...state, isFlipped: true }
    case 'SUBMIT_START':
      return { ...state, isSubmitting: true, error: null }
    case 'SUBMIT_DONE':
      return { ...state, isSubmitting: false, currentPosition: action.nextPosition, isFlipped: false }
    case 'ERROR':
      return { ...state, isSubmitting: false, error: action.message }
    case 'DISMISS_ERROR':
      return { ...state, error: null }
    default:
      return state
  }
}

const INITIAL_STATE: PracticeState = {
  currentPosition: 0,
  isFlipped: false,
  isSubmitting: false,
  startTime: Date.now(),
  error: null,
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function FlashcardPractice() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()
  const [state, dispatch] = useReducer(reducer, INITIAL_STATE)

  // Session summary query disabled until session ends (only used post-session)
  useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => api.getSessionSummary(Number(sessionId)),
    enabled: false,
  })

  // Fetch deck detail to get card list — passed via navigation state
  const deckId = Number(new URLSearchParams(window.location.search).get('deck_id'))
  const { data: deck, isLoading: deckLoading } = useQuery({
    queryKey: ['deck', deckId],
    queryFn: () => api.getDeck(deckId),
    enabled: !!deckId,
  })

  const currentCard = deck?.cards?.[state.currentPosition] ?? null
  const totalCards = deck?.cards?.length ?? 0
  const mode = deck?.practice_mode ?? 'recall'

  const handleRate = useCallback(
    async (rating: Rating) => {
      if (!currentCard) return
      dispatch({ type: 'SUBMIT_START' })
      try {
        await api.recordCardResult(Number(sessionId), state.currentPosition, rating)
        const nextPosition = state.currentPosition + 1
        if (nextPosition >= totalCards) {
          await api.endSession(Number(sessionId), true)
          navigate(`/flashcards/summary/${sessionId}`)
          return
        }
        dispatch({ type: 'SUBMIT_DONE', nextPosition })
      } catch (e) {
        dispatch({ type: 'ERROR', message: e instanceof Error ? e.message : 'Failed to record rating' })
      }
    },
    [currentCard, sessionId, state.currentPosition, totalCards, navigate],
  )

  async function handleExit() {
    try {
      await api.endSession(Number(sessionId), false)
    } finally {
      navigate(`/flashcards/summary/${sessionId}`)
    }
  }

  if (deckLoading) {
    return (
      <div style={{ textAlign: 'center', padding: '80px', color: 'var(--color-text-muted)' }}>
        Loading…
      </div>
    )
  }

  if (!deck || !currentCard) {
    return (
      <div style={{ textAlign: 'center', padding: '80px', color: 'var(--color-text-muted)' }}>
        No cards available.
      </div>
    )
  }

  const ttsUrl = currentCard.vocabulary_item_id
    ? api.getVocabTtsUrl(currentCard.vocabulary_item_id)
    : null

  return (
    <main
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        minHeight: '100vh',
        background: 'var(--color-bg)',
        padding: '24px 16px',
        gap: '16px',
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '560px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <span style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
          Card {state.currentPosition + 1} of {totalCards}
        </span>
        <button
          onClick={handleExit}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--color-text-muted)',
            cursor: 'pointer',
            fontSize: '0.85rem',
          }}
        >
          Exit
        </button>
      </div>

      {state.error && (
        <ErrorBanner message={state.error} onDismiss={() => dispatch({ type: 'DISMISS_ERROR' })} />
      )}

      <div
        style={{
          width: '100%',
          maxWidth: '560px',
          background: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius)',
          boxShadow: 'var(--shadow)',
          minHeight: '260px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
        }}
      >
        <CardPrompt
          card={currentCard}
          mode={mode}
          nativeWord={currentCard.translation ?? null}
          isFlipped={state.isFlipped}
          onFlip={() => dispatch({ type: 'FLIP' })}
        />

        {ttsUrl && (
          <div style={{ paddingBottom: '16px' }}>
            <AudioControls ttsUrl={ttsUrl} />
          </div>
        )}
      </div>

      {state.isFlipped && currentCard.vocabulary_item_id && (
        <div style={{ width: '100%', maxWidth: '560px' }}>
          <CardAnswer vocabularyItemId={currentCard.vocabulary_item_id} isFlipped={state.isFlipped} />
        </div>
      )}

      {state.isFlipped && !state.isSubmitting && (
        <div style={{ width: '100%', maxWidth: '560px' }}>
          <SelfAssessmentBar onRate={handleRate} />
        </div>
      )}

      {state.isSubmitting && (
        <p style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem' }}>Saving…</p>
      )}

      {/* Progress bar */}
      <div
        style={{
          width: '100%',
          maxWidth: '560px',
          height: '4px',
          background: 'var(--color-border)',
          borderRadius: '2px',
        }}
      >
        <div
          style={{
            height: '100%',
            width: `${((state.currentPosition) / totalCards) * 100}%`,
            background: 'var(--color-primary)',
            borderRadius: '2px',
            transition: 'width 0.3s ease',
          }}
        />
      </div>
    </main>
  )
}
