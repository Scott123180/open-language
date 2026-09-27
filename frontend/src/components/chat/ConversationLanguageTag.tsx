import type { CSSProperties } from 'react'

const tagStyle: CSSProperties = { fontWeight: 600, color: 'var(--color-text-muted)' }
const visuallyHidden: CSSProperties = {
  position: 'absolute',
  width: '1px',
  height: '1px',
  padding: 0,
  margin: '-1px',
  overflow: 'hidden',
  clip: 'rect(0, 0, 0, 0)',
  whiteSpace: 'nowrap',
  border: 0,
}

/** The conversation's language, as text: it is fixed for the conversation, so there is no control. */
export default function ConversationLanguageTag({ name }: { name: string }) {
  if (!name) return null
  return (
    <span style={tagStyle}>
      <span style={visuallyHidden}>Conversation language: </span>
      <span>{name}</span>
    </span>
  )
}
