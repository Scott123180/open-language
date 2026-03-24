import type { DeckCardItem, PracticeMode } from '../../services/flashcardsApi'

interface Props {
  card: DeckCardItem
  mode: PracticeMode
  nativeWord: string | null
  isFlipped: boolean
  onFlip: () => void
}

function getPrompt(card: DeckCardItem, mode: PracticeMode, nativeWord: string | null): string | null {
  if (mode === 'produce') return nativeWord
  if (mode === 'listen') return null
  if (mode === 'fill_blank') return card.fill_blank_sentence ?? null
  return card.word
}

function getAnswer(card: DeckCardItem, mode: PracticeMode, nativeWord: string | null): string | null {
  if (mode === 'produce') return card.word
  return nativeWord
}

export default function CardPrompt({ card, mode, nativeWord, isFlipped, onFlip }: Props) {
  const prompt = getPrompt(card, mode, nativeWord)
  const answer = getAnswer(card, mode, nativeWord)

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '24px',
        padding: '40px 24px',
      }}
    >
      {mode === 'listen' ? (
        <div
          style={{
            fontSize: '1rem',
            color: 'var(--color-text-muted)',
            textAlign: 'center',
          }}
          aria-label="Listen to the audio and recall the word"
        >
          🎧 Listen and recall
        </div>
      ) : (
        <div
          style={{
            fontSize: '2rem',
            fontWeight: 700,
            textAlign: 'center',
            color: 'var(--color-text)',
            minHeight: '3rem',
          }}
        >
          {prompt}
        </div>
      )}

      {isFlipped && (
        <>
          {mode === 'fill_blank' && (
            <div
              style={{
                fontSize: '1.5rem',
                textAlign: 'center',
                color: 'var(--color-text)',
                fontWeight: 600,
              }}
            >
              {card.word}
            </div>
          )}
          {answer && mode !== 'fill_blank' && (
            <div
              style={{
                fontSize: '1.5rem',
                textAlign: 'center',
                color: 'var(--color-text-muted)',
              }}
            >
              {answer}
            </div>
          )}
        </>
      )}

      {!isFlipped && (
        <button
          aria-label="Flip card"
          onClick={onFlip}
          style={{
            padding: '10px 28px',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius)',
            background: 'var(--color-surface)',
            color: 'var(--color-text)',
            fontSize: '0.95rem',
            cursor: 'pointer',
          }}
        >
          Flip
        </button>
      )}
    </div>
  )
}
