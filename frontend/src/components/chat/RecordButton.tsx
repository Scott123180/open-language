interface RecordButtonProps {
  isRecording: boolean
  isProcessing: boolean
  onStartRecording: () => void
  onStopRecording: () => void
}

const baseStyle: React.CSSProperties = {
  width: '44px',
  height: '44px',
  borderRadius: '50%',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontSize: '1.2rem',
  flexShrink: 0,
  outline: 'none',
  transition: 'box-shadow 0.15s, background 0.15s',
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
          background: 'var(--color-border)',
          color: 'var(--color-text-muted)',
          cursor: 'not-allowed',
        }}
      >
        <span aria-hidden='true'>⏳</span>
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
          background: '#dc2626',
          color: '#fff',
          animation: 'pulse 1.2s ease-in-out infinite',
          boxShadow: '0 0 0 4px rgba(220,38,38,0.3)',
        }}
      >
        <span aria-hidden='true'>⏹</span>
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
        color: '#fff',
      }}
    >
      <span aria-hidden='true'>🎤</span>
    </button>
  )
}
