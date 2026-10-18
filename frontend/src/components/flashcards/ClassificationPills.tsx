import type { WordClassification } from '../../services/flashcardsApi'
import { pillDotStyle, pillStyle } from './wordFilterStyles'

const CLASSIFICATION_FILTERS: { value: WordClassification; label: string; color: string }[] = [
  { value: 'not_practiced', label: 'Not Practiced', color: 'var(--color-text-muted)' },
  { value: 'difficult', label: 'Difficult', color: 'var(--color-error)' },
  { value: 'almost_learned', label: 'Almost Learned', color: 'var(--color-warning)' },
  { value: 'learned', label: 'Learned', color: 'var(--color-success)' },
]

interface ClassificationPillsProps {
  active: WordClassification[]
  onChange: (classifications: WordClassification[]) => void
}

/** One toggle per classification; several can be on at once. */
export default function ClassificationPills({ active, onChange }: ClassificationPillsProps) {
  const toggle = (value: WordClassification) =>
    onChange(active.includes(value) ? active.filter((c) => c !== value) : [...active, value])
  return (
    <>
      {CLASSIFICATION_FILTERS.map(({ value, label, color }) => {
        const isActive = active.includes(value)
        return (
          <button key={value} onClick={() => toggle(value)} aria-pressed={isActive} style={pillStyle(color, isActive)}>
            <span style={pillDotStyle(color, isActive)} />
            {label}
          </button>
        )
      })}
    </>
  )
}
