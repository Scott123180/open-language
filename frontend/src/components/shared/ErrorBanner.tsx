import { useState } from 'react'

interface ErrorBannerProps {
  message: string
  onDismiss?: () => void
}

export default function ErrorBanner({ message, onDismiss }: ErrorBannerProps) {
  const [visible, setVisible] = useState(true)

  if (!visible) return null

  const handleDismiss = () => {
    setVisible(false)
    onDismiss?.()
  }

  return (
    <div
      role="alert"
      aria-live="assertive"
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 16px',
        backgroundColor: '#fef2f2',
        border: '1px solid var(--color-error)',
        borderRadius: 'var(--radius)',
        color: 'var(--color-error)',
        gap: '12px',
      }}
    >
      <span>{message}</span>
      <button
        onClick={handleDismiss}
        aria-label="Dismiss error"
        style={{
          background: 'none',
          color: 'var(--color-error)',
          fontSize: '1.25rem',
          lineHeight: 1,
          padding: '0 4px',
          flexShrink: 0,
        }}
      >
        &times;
      </button>
    </div>
  )
}
