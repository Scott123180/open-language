import type { Rating } from '../../services/flashcardsApi'

interface Props {
  onRate: (rating: Rating) => void
}

interface RatingOption {
  rating: Rating
  label: string
  bg: string
  color: string
  border: string
}

const RATINGS: RatingOption[] = [
  {
    rating: 'didnt_know',
    label: "Didn't Know",
    bg: 'var(--color-error-subtle)',
    color: 'var(--color-error)',
    border: 'var(--color-error)',
  },
  {
    rating: 'guessed',
    label: 'Guessed',
    bg: 'var(--color-surface-raised)',
    color: 'var(--color-warning)',
    border: 'var(--color-warning)',
  },
  {
    rating: 'knew_it',
    label: 'Knew It',
    bg: 'var(--color-success-subtle)',
    color: 'var(--color-success)',
    border: 'var(--color-success)',
  },
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
      {RATINGS.map(({ rating, label, bg, color, border }) => (
        <button
          key={rating}
          aria-label={label}
          onClick={() => onRate(rating)}
          style={{
            padding: '10px 20px',
            borderRadius: 'var(--radius)',
            border: `1px solid ${border}`,
            background: bg,
            color: color,
            fontWeight: 'var(--weight-semibold)' as never,
            fontSize: 'var(--text-sm)',
            cursor: 'pointer',
            transition: 'var(--transition-base)',
          }}
        >
          {label}
        </button>
      ))}
    </div>
  )
}
