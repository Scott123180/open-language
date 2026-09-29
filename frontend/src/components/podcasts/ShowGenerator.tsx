import { useState, type FormEvent } from 'react'
import { fieldsetStyle, legendStyle, mutedTextStyle, secondaryButtonStyle } from './styles'

interface ShowGeneratorProps {
  onGenerate: (idea: string) => void
  onSurprise: () => void
  isPending: boolean
  error: string | null
}

const inputStyle = {
  minHeight: '44px',
  padding: '0 var(--space-3)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-md)',
  background: 'var(--color-surface)',
  color: 'var(--color-text)',
  font: 'inherit',
}

/** A show from the learner's own idea, or a surprise (FR-020, FR-022). Both are secondary to
 * choosing a ready-made show, so neither uses the primary button style. */
export default function ShowGenerator({ onGenerate, onSurprise, isPending, error }: ShowGeneratorProps) {
  const [idea, setIdea] = useState('')
  const submit = (event: FormEvent) => {
    event.preventDefault()
    onGenerate(idea)
  }
  return (
    <form onSubmit={submit} style={fieldsetStyle} aria-busy={isPending}>
      <label htmlFor="show-idea" style={legendStyle}>Your show idea</label>
      <input id="show-idea" value={idea} maxLength={200} placeholder="e.g. living abroad as a nurse" onChange={(e) => setIdea(e.target.value)} style={inputStyle} />
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
        <button type="submit" disabled={isPending} style={secondaryButtonStyle}>Generate</button>
        <button type="button" onClick={onSurprise} disabled={isPending} style={secondaryButtonStyle}>Surprise me</button>
      </div>
      {isPending && <p role="status" style={{ ...mutedTextStyle, margin: 0 }}>Creating your show…</p>}
      {error && <p role="alert" style={{ margin: 0, color: 'var(--color-error)' }}>{error}</p>}
    </form>
  )
}
