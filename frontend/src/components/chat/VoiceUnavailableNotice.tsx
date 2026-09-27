import type { CSSProperties } from 'react'

const noticeStyle: CSSProperties = {
  margin: '8px 16px 0',
  padding: '8px 12px',
  background: 'var(--color-surface)',
  color: 'var(--color-text-muted)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-lg)',
  fontSize: '0.85rem',
}

/** One persistent note that this conversation can't be read aloud, and what to do (FR-018). */
export default function VoiceUnavailableNotice({ message }: { message: string | null }) {
  if (!message) return null
  return (
    <p role="status" style={noticeStyle}>
      {message}
    </p>
  )
}
