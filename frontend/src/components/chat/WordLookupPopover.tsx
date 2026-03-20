import ReactMarkdown from 'react-markdown'

const POPOVER_WIDTH = 420
const POPOVER_MARGIN = 12

interface WordLookupPopoverProps {
  word: string
  result: string | null
  isLoading: boolean
  onSave?: (word: string) => void
  onClose: () => void
  position?: { x: number; y: number }
}

const spinnerStyle: React.CSSProperties = {
  display: 'inline-block',
  width: '14px',
  height: '14px',
  border: '2px solid var(--color-border)',
  borderTopColor: 'var(--color-primary)',
  borderRadius: '50%',
  animation: 'spin 0.6s linear infinite',
}

export default function WordLookupPopover({
  word,
  result,
  isLoading,
  onSave,
  onClose,
  position,
}: WordLookupPopoverProps) {
  const clampedLeft = position
    ? Math.min(
        Math.max(position.x - POPOVER_WIDTH / 2, POPOVER_MARGIN),
        window.innerWidth - POPOVER_WIDTH - POPOVER_MARGIN,
      )
    : undefined

  const fitsBelow = position
    ? position.y + 8 + window.innerHeight * 0.6 < window.innerHeight - 16
    : true

  const popoverStyle: React.CSSProperties = {
    position: 'fixed',
    left: clampedLeft != null ? `${clampedLeft}px` : '50%',
    top: position
      ? fitsBelow
        ? `${position.y + 8}px`
        : undefined
      : '50%',
    bottom: position && !fitsBelow ? `${window.innerHeight - position.y + 8}px` : undefined,
    transform: clampedLeft == null ? 'translate(-50%, -50%)' : undefined,
    zIndex: 1001,
    background: 'var(--color-surface)',
    border: '1px solid var(--color-border)',
    borderRadius: 'var(--radius)',
    boxShadow: '0 4px 16px rgba(0,0,0,0.2)',
    padding: '12px 14px',
    minWidth: '240px',
    width: `${POPOVER_WIDTH}px`,
    maxWidth: `calc(100vw - ${POPOVER_MARGIN * 2}px)`,
    maxHeight: '60vh',
    overflowY: 'auto',
  }

  return (
    <>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      {/* Backdrop — click anywhere outside to close */}
      <div
        aria-hidden="true"
        onClick={onClose}
        style={{ position: 'fixed', inset: 0, zIndex: 1000 }}
      />
      <div role="dialog" aria-label="Word lookup" style={popoverStyle}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '8px',
          }}
        >
          <strong style={{ fontSize: '0.95rem', color: 'var(--color-text)' }}>{word}</strong>
          <button
            aria-label="Close"
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              fontSize: '1rem',
              color: 'var(--color-text-muted)',
              padding: '0 2px',
              lineHeight: 1,
            }}
          >
            ×
          </button>
        </div>

        <div style={{ fontSize: '0.85rem', color: 'var(--color-text)', marginBottom: '10px', minHeight: '20px' }}>
          {isLoading ? (
            <span role="status" style={spinnerStyle} />
          ) : result ? (
            <ReactMarkdown
              components={{
                p: ({ children }) => <p style={{ margin: '0 0 6px' }}>{children}</p>,
                strong: ({ children }) => <strong style={{ color: 'var(--color-text)' }}>{children}</strong>,
                ul: ({ children }) => <ul style={{ margin: '4px 0', paddingLeft: '16px' }}>{children}</ul>,
                ol: ({ children }) => <ol style={{ margin: '4px 0', paddingLeft: '16px' }}>{children}</ol>,
                li: ({ children }) => <li style={{ marginBottom: '2px' }}>{children}</li>,
              }}
            >
              {result}
            </ReactMarkdown>
          ) : null}
        </div>

        {onSave && (
          <button
            onClick={() => onSave(word)}
            disabled={!result}
            style={{
              width: '100%',
              padding: '6px 12px',
              background: result ? 'var(--color-primary)' : 'var(--color-border)',
              color: result ? '#fff' : 'var(--color-text-muted)',
              borderRadius: 'var(--radius)',
              fontSize: '0.82rem',
              fontWeight: 600,
              cursor: result ? 'pointer' : 'not-allowed',
            }}
          >
            Save Word
          </button>
        )}
      </div>
    </>
  )
}
