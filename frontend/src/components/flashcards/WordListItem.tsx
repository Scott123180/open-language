import { useState } from 'react'
import type { WordClassification, WordListItem as WordListItemType } from '../../services/flashcardsApi'
import { IconTrash } from '../shared/icons'

interface Props {
  word: WordListItemType
  onDelete: (id: number) => void
  isSelected?: boolean
  onToggleSelect?: (id: number) => void
}

const CLASSIFICATION_META: Record<WordClassification, { label: string; color: string }> = {
  not_practiced:  { label: 'Not Practiced',  color: 'var(--color-text-muted)' },
  difficult:      { label: 'Difficult',      color: 'var(--color-error)'      },
  almost_learned: { label: 'Almost Learned', color: 'var(--color-warning)'    },
  learned:        { label: 'Learned',        color: 'var(--color-success)'    },
}

export default function WordListItem({ word, onDelete, isSelected = false, onToggleSelect }: Props) {
  const [pendingDelete, setPendingDelete] = useState(false)
  const meta = CLASSIFICATION_META[word.classification] ?? CLASSIFICATION_META.not_practiced

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: onToggleSelect ? 'auto minmax(120px, 28%) 1fr auto' : 'minmax(120px, 28%) 1fr auto',
        alignItems: 'center',
        padding: 'var(--space-3) var(--space-4)',
        borderBottom: '1px solid var(--color-border)',
        background: 'var(--color-surface)',
        borderLeft: `3px solid ${meta.color}`,
        gap: 'var(--space-3)',
        transition: 'background 0.1s',
      }}
      onMouseEnter={(e) => ((e.currentTarget as HTMLDivElement).style.background = 'var(--color-bg)')}
      onMouseLeave={(e) => ((e.currentTarget as HTMLDivElement).style.background = 'var(--color-surface)')}
    >
      {/* Selection checkbox */}
      {onToggleSelect && (
        <input
          type="checkbox"
          checked={isSelected}
          onChange={() => onToggleSelect(word.id)}
          aria-label={`Select ${word.word}`}
          style={{ cursor: 'pointer', flexShrink: 0, accentColor: 'var(--color-primary)' }}
        />
      )}

      {/* Word */}
      <span
        style={{
          fontWeight: 600,
          fontSize: 'var(--text-base)',
          color: 'var(--color-text)',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}
      >
        {word.word}
      </span>

      {/* Translation */}
      <span
        style={{
          color: 'var(--color-text-muted)',
          fontSize: 'var(--text-sm)',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}
      >
        {word.translation}
      </span>

      {/* Status badge + delete */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', flexShrink: 0 }}>
        <span
          style={{
            padding: '2px 8px',
            borderRadius: 'var(--radius-full)',
            fontSize: 'var(--text-xs)',
            fontWeight: 600,
            color: meta.color,
            background: `color-mix(in srgb, ${meta.color} 12%, transparent)`,
            whiteSpace: 'nowrap',
            letterSpacing: '0.01em',
          }}
        >
          {meta.label}
        </span>

        {pendingDelete ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <button
              onClick={() => onDelete(word.id)}
              style={{
                background: 'var(--color-error)',
                border: 'none',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--color-text-on-primary)',
                cursor: 'pointer',
                fontSize: 'var(--text-xs)',
                fontWeight: 600,
                padding: '3px 8px',
                whiteSpace: 'nowrap',
                minHeight: 'unset',
              }}
            >
              Delete?
            </button>
            <button
              onClick={() => setPendingDelete(false)}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--color-text-muted)',
                cursor: 'pointer',
                fontSize: 'var(--text-xs)',
                padding: '3px 4px',
                minHeight: 'unset',
              }}
            >
              Cancel
            </button>
          </div>
        ) : (
          <button
            aria-label={`Delete ${word.word}`}
            onClick={() => setPendingDelete(true)}
            style={{
              background: 'none',
              border: 'none',
              padding: '4px',
              borderRadius: 'var(--radius-sm)',
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
            onMouseEnter={(e) => ((e.currentTarget as HTMLButtonElement).style.color = 'var(--color-error)')}
            onMouseLeave={(e) => ((e.currentTarget as HTMLButtonElement).style.color = 'var(--color-text-muted)')}
          >
            <IconTrash size={15} />
          </button>
        )}
      </div>
    </div>
  )
}
