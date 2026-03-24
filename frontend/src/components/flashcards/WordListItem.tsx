import type { WordClassification, WordListItem as WordListItemType } from '../../services/flashcardsApi'
import { IconTrash } from '../shared/icons'

interface Props {
  word: WordListItemType
  onDelete: (id: number) => void
  onClassify: (id: number, classification: WordClassification) => void
}

const CLASSIFICATION_META: Record<WordClassification, { label: string; color: string; bg: string }> = {
  not_practiced:  { label: 'Not Practiced',  color: '#64748b', bg: 'rgba(100,116,139,0.12)' },
  difficult:      { label: 'Difficult',      color: '#ef4444', bg: 'rgba(239,68,68,0.10)'   },
  almost_learned: { label: 'Almost Learned', color: '#f59e0b', bg: 'rgba(245,158,11,0.10)'  },
  learned:        { label: 'Learned',        color: '#22c55e', bg: 'rgba(34,197,94,0.10)'   },
}

const CLASSIFICATION_ORDER: WordClassification[] = [
  'not_practiced',
  'difficult',
  'almost_learned',
  'learned',
]

export default function WordListItem({ word, onDelete, onClassify }: Props) {
  const meta = CLASSIFICATION_META[word.classification] ?? CLASSIFICATION_META.not_practiced

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        padding: '10px 16px',
        borderBottom: '1px solid var(--color-border)',
        background: 'var(--color-surface)',
        borderLeft: `3px solid ${meta.color}`,
        gap: '12px',
        transition: 'background 0.1s',
      }}
      onMouseEnter={(e) => ((e.currentTarget as HTMLDivElement).style.background = 'var(--color-bg)')}
      onMouseLeave={(e) => ((e.currentTarget as HTMLDivElement).style.background = 'var(--color-surface)')}
    >
      {/* Word + translation */}
      <div style={{ flex: 1, minWidth: 0, display: 'flex', alignItems: 'baseline', gap: '8px' }}>
        <span
          style={{
            fontWeight: 600,
            fontSize: '0.95rem',
            color: 'var(--color-text)',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {word.word}
        </span>
        <span style={{ color: 'var(--color-text-muted)', fontSize: '0.8rem', flexShrink: 0 }}>→</span>
        <span
          style={{
            color: 'var(--color-text-muted)',
            fontSize: '0.88rem',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {word.translation}
        </span>
      </div>

      {/* Classification badge */}
      <span
        style={{
          padding: '2px 8px',
          borderRadius: '999px',
          fontSize: '0.72rem',
          fontWeight: 600,
          color: meta.color,
          background: meta.bg,
          whiteSpace: 'nowrap',
          flexShrink: 0,
          letterSpacing: '0.01em',
        }}
      >
        {meta.label}
      </span>

      {/* Reclassify select */}
      <select
        aria-label="Change classification"
        value={word.classification}
        onChange={(e) => onClassify(word.id, e.target.value as WordClassification)}
        style={{
          fontSize: '0.8rem',
          padding: '3px 6px',
          background: 'var(--color-bg)',
          color: 'var(--color-text)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius)',
          cursor: 'pointer',
          outline: 'none',
          flexShrink: 0,
          minHeight: '28px',
          minWidth: 'unset',
        }}
        onFocus={(e) => (e.currentTarget.style.borderColor = 'var(--color-primary)')}
        onBlur={(e) => (e.currentTarget.style.borderColor = 'var(--color-border)')}
      >
        {CLASSIFICATION_ORDER.map((cls) => (
          <option key={cls} value={cls}>
            {CLASSIFICATION_META[cls].label}
          </option>
        ))}
      </select>

      {/* Delete button */}
      <button
        aria-label={`Delete ${word.word}`}
        onClick={() => onDelete(word.id)}
        style={{
          background: 'none',
          border: 'none',
          padding: '4px',
          borderRadius: 'var(--radius)',
          color: 'var(--color-text-muted)',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
          minHeight: '28px',
          minWidth: '28px',
          transition: 'color 0.15s',
        }}
        onMouseEnter={(e) => ((e.currentTarget as HTMLButtonElement).style.color = '#ef4444')}
        onMouseLeave={(e) => ((e.currentTarget as HTMLButtonElement).style.color = 'var(--color-text-muted)')}
      >
        <IconTrash size={15} />
      </button>
    </div>
  )
}
