import { mutedTextStyle } from './styles'

export const LEARNER_NAME_MAX_LENGTH = 40
const INPUT_ID = 'podcast-learner-name'
const HINT_ID = 'podcast-learner-name-hint'

interface LearnerNameFieldProps {
  value: string
  onChange: (name: string) => void
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

/** The name the hosts call the learner; blank means "our guest" (FR-011). */
export default function LearnerNameField({ value, onChange }: LearnerNameFieldProps) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
      <label htmlFor={INPUT_ID} style={{ color: 'var(--color-text)' }}>Your name (optional)</label>
      <input id={INPUT_ID} aria-describedby={HINT_ID} maxLength={LEARNER_NAME_MAX_LENGTH} value={value} onChange={(e) => onChange(e.target.value)} style={inputStyle} />
      <span id={HINT_ID} style={mutedTextStyle}>Leave it blank and the hosts call you “our guest”.</span>
    </div>
  )
}
