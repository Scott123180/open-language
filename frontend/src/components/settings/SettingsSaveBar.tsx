import type { CSSProperties, MouseEvent } from 'react'
import { errorTextStyle, successTextStyle } from './settingsStyles'

interface SettingsSaveBarProps {
  isSaving: boolean
  successMessage: string | null
  errorMessage: string | null
  onSave: () => void
}

const saveButtonStyle = (isSaving: boolean): CSSProperties => ({
  padding: '12px 24px',
  background: isSaving ? 'var(--color-border)' : 'var(--color-primary)',
  color: isSaving ? 'var(--color-text-muted)' : 'var(--color-text-on-primary)',
  borderRadius: 'var(--radius)',
  fontWeight: 600,
  fontSize: '1rem',
  cursor: isSaving ? 'not-allowed' : 'pointer',
  border: 'none',
})

/** The save outcome and the screen's one primary action. */
export default function SettingsSaveBar({
  isSaving,
  successMessage,
  errorMessage,
  onSave,
}: SettingsSaveBarProps) {
  // Pressing Enter in a field clicks the submit button, so this one handler covers both.
  const save = (event: MouseEvent<HTMLButtonElement>) => {
    event.preventDefault()
    onSave()
  }
  return (
    <>
      <SaveOutcome successMessage={successMessage} errorMessage={errorMessage} />
      <button type="submit" disabled={isSaving} onClick={save} style={saveButtonStyle(isSaving)}>
        {isSaving ? 'Saving…' : 'Save'}
      </button>
    </>
  )
}

type SaveOutcomeProps = Pick<SettingsSaveBarProps, 'successMessage' | 'errorMessage'>

function SaveOutcome({ successMessage, errorMessage }: SaveOutcomeProps) {
  return (
    <>
      {successMessage && (
        <p role="status" style={successTextStyle}>
          {successMessage}
        </p>
      )}
      {errorMessage && (
        <p role="alert" style={errorTextStyle}>
          {errorMessage}
        </p>
      )}
    </>
  )
}
