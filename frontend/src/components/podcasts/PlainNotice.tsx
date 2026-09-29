import { mutedTextStyle } from './styles'

/** A plain status line, announced to screen readers; renders nothing without a message. */
export default function PlainNotice({ message }: { message: string | null | undefined }) {
  if (!message) return null
  return (
    <p role="status" style={{ ...mutedTextStyle, margin: 0, color: 'var(--color-text)' }}>
      {message}
    </p>
  )
}
