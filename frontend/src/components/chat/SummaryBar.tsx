import type { ReactNode } from 'react'
import SummaryButton from './SummaryButton'

interface SummaryBarProps {
  conversationId: number
  lastMessageId?: number
  children?: ReactNode
}

const barStyle = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'flex-end',
  gap: 'var(--space-2)',
  padding: 'var(--space-1) var(--space-4)',
  borderBottom: '1px solid var(--color-border)',
  background: 'var(--color-surface)',
}

/** The conversation's secondary tools under its header: Summary, and any a screen adds.
 * Kept out of the header grid, which has no spare width at 360 px (Principle IV). */
export default function SummaryBar({ conversationId, lastMessageId, children }: SummaryBarProps) {
  return (
    <div style={barStyle}>
      {children}
      <SummaryButton conversationId={conversationId} lastMessageId={lastMessageId} />
    </div>
  )
}
