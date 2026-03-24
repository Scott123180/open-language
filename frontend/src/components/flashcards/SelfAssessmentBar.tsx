import type { Rating } from '../../services/flashcardsApi'

interface Props {
  onRate: (rating: Rating) => void
}

const RATINGS: Array<{ rating: Rating; label: string; color: string }> = [
  { rating: 'didnt_know', label: "Didn't Know", color: '#ef4444' },
  { rating: 'guessed', label: 'Guessed Correctly', color: '#f59e0b' },
  { rating: 'knew_it', label: 'Knew It', color: '#22c55e' },
]

export default function SelfAssessmentBar({ onRate }: Props) {
  return (
    <div
      style={{
        display: 'flex',
        gap: '12px',
        justifyContent: 'center',
        padding: '16px',
        flexWrap: 'wrap',
      }}
    >
      {RATINGS.map(({ rating, label, color }) => (
        <button
          key={rating}
          aria-label={label}
          onClick={() => onRate(rating)}
          style={{
            padding: '10px 20px',
            borderRadius: 'var(--radius)',
            border: `2px solid ${color}`,
            background: 'transparent',
            color: color,
            fontWeight: 600,
            fontSize: '0.9rem',
            cursor: 'pointer',
          }}
        >
          {label}
        </button>
      ))}
    </div>
  )
}
