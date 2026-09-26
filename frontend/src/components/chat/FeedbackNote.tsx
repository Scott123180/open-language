import type { FeedbackNoteData } from '../../services/api'

interface FeedbackNoteProps {
  note: FeedbackNoteData
}

const CATEGORY_LABELS: Record<string, string> = {
  conjugation: 'Conjugation',
  agreement: 'Agreement',
  word_choice: 'Word choice',
  word_order: 'Word order',
}

const noteStyle: React.CSSProperties = {
  borderLeft: '3px solid var(--color-warning)',
  background: 'var(--color-surface-raised)',
  borderRadius: 'var(--radius-lg)',
  boxShadow: 'var(--shadow-sm)',
  padding: '10px 14px',
  display: 'flex',
  flexDirection: 'column',
  gap: '4px',
  lineHeight: 'var(--leading-relaxed)',
}

/**
 * An app note attached to the learner's own message — never character dialogue,
 * and never spoken: it lives outside `messages.content`, so TTS cannot reach it.
 */
export default function FeedbackNote({ note }: FeedbackNoteProps) {
  const heading =
    note.kind === 'repeat_request'
      ? 'Could you repeat that?'
      : CATEGORY_LABELS[note.category ?? ''] ?? 'Correction'

  return (
    <aside role="note" aria-label="Learning feedback" style={noteStyle}>
      <span style={{ fontWeight: 600, fontSize: '0.8rem', color: 'var(--color-warning)' }}>
        {heading}
      </span>

      {note.error_fragment && (
        <span style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
          You wrote: <s>{note.error_fragment}</s>
        </span>
      )}

      {note.corrected_text && (
        <span style={{ fontWeight: 600, color: 'var(--color-text)' }}>{note.corrected_text}</span>
      )}

      <span style={{ fontSize: '0.875rem', color: 'var(--color-text)' }}>{note.explanation}</span>
    </aside>
  )
}
