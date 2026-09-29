import RecordButton from '../chat/RecordButton'
import { IconMessageCircle } from '../shared/icons'
import type { LearnerInput } from '../../hooks/podcasts/useLearnerInput'
import { primaryButtonStyle, secondaryButtonStyle } from './styles'

interface ComposerBarProps {
  input: LearnerInput
  isDisabled: boolean
  isAwaitingRetry: boolean
  isHelperOpen: boolean
  onToggleHelper: () => void
}

const inputStyle = {
  flex: 1,
  minHeight: '44px',
  padding: '0 var(--space-3)',
  background: 'var(--color-surface)',
  color: 'var(--color-text)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-md)',
  font: 'inherit',
}

/** Record, type and send, as in chat: the learner's turn has one primary action. */
export default function ComposerBar({ input, isDisabled, isAwaitingRetry, isHelperOpen, onToggleHelper }: ComposerBarProps) {
  const disabled = isDisabled || input.isRecording || input.isTranscribing
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
      <RecordButton isRecording={input.isRecording} isProcessing={input.isTranscribing} onStartRecording={input.startRecording} onStopRecording={input.stopRecording} />
      <input type="text" aria-label="Type a message" value={input.text} disabled={disabled} placeholder={isAwaitingRetry ? 'Try again…' : 'Type a message…'} onChange={(e) => input.setText(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && input.submit()} style={inputStyle} />
      <button type="button" aria-label="Send message" onClick={input.submit} disabled={disabled || !input.text.trim()} style={primaryButtonStyle}>Send ↑</button>
      <button type="button" aria-label={isHelperOpen ? 'Close expression helper' : 'Open expression helper'} onClick={onToggleHelper} style={secondaryButtonStyle}>
        <IconMessageCircle size={18} />
      </button>
    </div>
  )
}
