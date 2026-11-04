import type { SuggestionPhase } from '../../hooks/podcasts/useSubjectSuggestions'
import { mutedTextStyle, secondaryButtonStyle } from './styles'

interface SubjectSuggestionsProps {
  phase: SuggestionPhase
  subjects: string[]
  message: string | null
  ask: () => void
  onChoose: (subject: string) => void
}

const NOTHING_NEW = 'No new subjects came back. Type one, or start without one.'

/** Suggest subjects: a secondary button, and the subjects it found in a polite live region. */
export default function SubjectSuggestions({ phase, subjects, message, ask, onChoose }: SubjectSuggestionsProps) {
  const isWaiting = phase === 'waiting'
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', alignItems: 'flex-start' }}>
      <button type="button" onClick={ask} disabled={isWaiting} style={secondaryButtonStyle}>Suggest subjects</button>
      <div role="status" aria-live="polite" aria-busy={isWaiting}>
        {isWaiting && <span style={mutedTextStyle}>Finding subjects…</span>}
        {phase === 'shown' && <SubjectList subjects={subjects} onChoose={onChoose} />}
        {phase === 'empty' && <span style={mutedTextStyle}>{NOTHING_NEW}</span>}
        {phase === 'error' && <span style={mutedTextStyle}>{message}</span>}
      </div>
    </div>
  )
}

function SubjectList({ subjects, onChoose }: { subjects: string[]; onChoose: (subject: string) => void }) {
  return (
    <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
      {subjects.map((subject) => (
        <li key={subject}>
          <button type="button" aria-label={`Use: ${subject}`} onClick={() => onChoose(subject)} style={secondaryButtonStyle}>{subject}</button>
        </li>
      ))}
    </ul>
  )
}
