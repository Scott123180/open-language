export type TurnStatus = 'idle' | 'checking' | 'replying'

interface TurnStatusIndicatorProps {
  status: TurnStatus
}

/**
 * Makes the evaluation wait legible (research.md R11): while the sentence is
 * being checked there is no character bubble yet, so this line stands in for it.
 */
export default function TurnStatusIndicator({ status }: TurnStatusIndicatorProps) {
  if (status !== 'checking') return null

  return (
    <p
      role="status"
      aria-live="polite"
      style={{
        margin: '4px 0 12px',
        fontSize: '0.875rem',
        color: 'var(--color-text-muted)',
        fontStyle: 'italic',
      }}
    >
      Checking your sentence…
    </p>
  )
}
