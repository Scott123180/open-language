import { useState } from 'react'
import { mutedTextStyle, secondaryButtonStyle } from './styles'

interface InterestsEditorProps {
  interests: string[]
  onSave: (interests: string[]) => Promise<void>
  error: string | null
}

const toList = (text: string) => text.split(',').map((item) => item.trim()).filter(Boolean)

/** The learner's interests, which Surprise me and the generator lean on (FR-023). They are
 * only ever what the learner typed here; nothing else writes them. */
export default function InterestsEditor({ interests, onSave, error }: InterestsEditorProps) {
  const [text, setText] = useState<string | null>(null)
  const shown = text ?? interests.join(', ')
  const clear = () => {
    setText('')
    void onSave([])
  }
  return (
    <details style={{ color: 'var(--color-text)' }}>
      <summary style={{ minHeight: '44px', display: 'flex', alignItems: 'center', cursor: 'pointer' }}>Your interests</summary>
      <label htmlFor="podcast-interests" style={{ ...mutedTextStyle, display: 'block' }}>Interests, separated by commas (up to 10)</label>
      <input id="podcast-interests" value={shown} onChange={(e) => setText(e.target.value)} style={{ minHeight: '44px', width: '100%', padding: '0 var(--space-3)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', background: 'var(--color-surface)', color: 'var(--color-text)', font: 'inherit', boxSizing: 'border-box' }} />
      <div style={{ display: 'flex', gap: 'var(--space-2)', marginTop: 'var(--space-2)' }}>
        <button type="button" onClick={() => void onSave(toList(shown))} style={secondaryButtonStyle}>Save interests</button>
        <button type="button" onClick={clear} style={secondaryButtonStyle}>Clear</button>
      </div>
      {error && <p role="alert" style={{ margin: 0, color: 'var(--color-error)' }}>{error}</p>}
    </details>
  )
}
