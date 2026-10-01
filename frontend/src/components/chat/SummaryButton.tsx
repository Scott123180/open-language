import { useState } from 'react'
import type { CSSProperties } from 'react'
import SummaryPanel from './SummaryPanel'

interface SummaryButtonProps {
  conversationId: number
  lastMessageId?: number
}

const buttonStyle: CSSProperties = {
  minHeight: '44px',
  padding: '0 var(--space-3)',
  background: 'transparent',
  color: 'var(--color-text)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-md)',
  fontSize: 'var(--text-sm)',
  cursor: 'pointer',
}
const panelPosition: CSSProperties = {
  position: 'absolute',
  top: 'calc(100% + var(--space-2))',
  right: 0,
  zIndex: 10,
  width: 'min(420px, calc(100vw - 32px))',
}

/** Summary: a secondary header action opening a non-modal panel over the transcript, so
 * nothing in the conversation moves when it opens or closes (FR-035, FR-041). */
export default function SummaryButton({ conversationId, lastMessageId }: SummaryButtonProps) {
  const [isOpen, setIsOpen] = useState(false)
  return (
    <div style={{ position: 'relative' }}>
      <button type="button" aria-expanded={isOpen} onClick={() => setIsOpen((open) => !open)} style={buttonStyle}>
        Summary
      </button>
      {isOpen && (
        <div style={panelPosition}>
          <SummaryPanel conversationId={conversationId} lastMessageId={lastMessageId} />
        </div>
      )}
    </div>
  )
}
