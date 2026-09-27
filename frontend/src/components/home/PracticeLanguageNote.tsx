import type { CSSProperties } from 'react'
import { Link } from 'react-router-dom'
import { usePracticeLanguages } from '../../hooks/usePracticeLanguages'

const noteStyle: CSSProperties = {
  margin: 0,
  padding: '8px 20px 0',
  textAlign: 'center',
  fontSize: '0.875rem',
  color: 'var(--color-text-muted)',
}
const nameStyle: CSSProperties = { color: 'var(--color-text)' }
// Muted like the sentence around it, so the underline is what marks it as a link.
const linkStyle: CSSProperties = { textDecoration: 'underline', minHeight: '44px' }

/** Which language new conversations are in, and where to change it (FR-004). */
export default function PracticeLanguageNote() {
  const { current } = usePracticeLanguages()
  if (current === null) return null
  return (
    <p style={noteStyle}>
      Practising <strong style={nameStyle}>{current.display_name}</strong> ·{' '}
      <Link to="/settings" className="back-link" style={linkStyle}>
        Change in Settings
      </Link>
    </p>
  )
}
