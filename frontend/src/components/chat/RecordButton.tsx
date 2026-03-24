import { IconMic, IconStop } from '../shared/icons'

interface RecordButtonProps {
  isRecording: boolean
  isProcessing: boolean
  onStartRecording: () => void
  onStopRecording: () => void
}

const spinnerStyle: React.CSSProperties = {
  display: 'inline-block',
  width: '18px',
  height: '18px',
  border: '2px solid var(--color-border)',
  borderTopColor: 'var(--color-text-muted)',
  borderRadius: '50%',
  animation: 'spin 0.6s linear infinite',
}

const baseStyle: React.CSSProperties = {
  width: '44px',
  height: '44px',
  borderRadius: '50%',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  flexShrink: 0,
  outline: 'none',
  transition: 'box-shadow var(--transition-base), background var(--transition-base)',
}

export default function RecordButton({
  isRecording,
  isProcessing,
  onStartRecording,
  onStopRecording,
}: RecordButtonProps) {
  if (isProcessing) {
    return (
      <button
        aria-label='Processing…'
        disabled
        style={{
          ...baseStyle,
          background: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
          cursor: 'not-allowed',
        }}
      >
        <span role="status" style={spinnerStyle} />
      </button>
    )
  }

  if (isRecording) {
    return (
      <button
        aria-label='Stop recording'
        onClick={onStopRecording}
        style={{
          ...baseStyle,
          background: 'var(--color-error)',
          color: 'var(--color-text-on-primary)',
          animation: 'pulse 1.2s ease-in-out infinite',
        }}
      >
        <IconStop size={18} strokeWidth={2} />
      </button>
    )
  }

  return (
    <button
      aria-label='Start recording'
      onClick={onStartRecording}
      style={{
        ...baseStyle,
        background: 'var(--color-primary)',
        color: 'var(--color-text-on-primary)',
      }}
    >
      <IconMic size={18} strokeWidth={2} />
    </button>
  )
}
