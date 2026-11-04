import { forwardRef } from 'react'
import { mutedTextStyle } from './styles'

const INPUT_ID = 'podcast-today-subject'
const COUNT_ID = 'podcast-today-subject-count'
const ERROR_ID = 'podcast-today-subject-error'

interface TodaySubjectFieldProps {
  value: string
  maxLength: number
  onChange: (subject: string) => void
  /** A declined subject's plain message, shown beside the field (FR-010). */
  error: string | null
}

const inputStyle = {
  minHeight: '44px',
  padding: '0 var(--space-3)',
  background: 'var(--color-surface)',
  color: 'var(--color-text)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-md)',
  font: 'inherit',
}

/** Today's subject: what this episode is about, if the learner wants to say (FR-010). */
const TodaySubjectField = forwardRef<HTMLInputElement, TodaySubjectFieldProps>(function TodaySubjectField({ value, maxLength, onChange, error }, ref) {
  const describedBy = error ? `${COUNT_ID} ${ERROR_ID}` : COUNT_ID
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
      <label htmlFor={INPUT_ID} style={{ color: 'var(--color-text)' }}>Today&apos;s subject (optional)</label>
      <input id={INPUT_ID} ref={ref} maxLength={maxLength} value={value} aria-invalid={error ? true : undefined} aria-describedby={describedBy} onChange={(e) => onChange(e.target.value)} style={inputStyle} />
      <span id={COUNT_ID} aria-live="polite" style={mutedTextStyle}>{`${value.length} / ${maxLength}`}</span>
      {error && <span id={ERROR_ID} role="alert" style={{ ...mutedTextStyle, color: 'var(--color-warning-text)' }}>{error}</span>}
    </div>
  )
})

export default TodaySubjectField
