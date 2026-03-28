import type { WordClassification, WordFilters, WordSort } from '../../services/flashcardsApi'
import { IconSearch } from '../shared/icons'

interface Props {
  filters: WordFilters
  onChange: (filters: WordFilters) => void
  sort: WordSort
  onSortChange: (sort: WordSort) => void
  isSelecting: boolean
  onToggleSelecting: () => void
  hasWords: boolean
}

const CLASSIFICATION_FILTERS: { value: WordClassification; label: string; color: string }[] = [
  { value: 'not_practiced',  label: 'Not Practiced',  color: 'var(--color-text-muted)' },
  { value: 'difficult',      label: 'Difficult',      color: 'var(--color-error)'      },
  { value: 'almost_learned', label: 'Almost Learned', color: 'var(--color-warning)'    },
  { value: 'learned',        label: 'Learned',        color: 'var(--color-success)'    },
]

const SORT_OPTIONS: { value: WordSort; label: string }[] = [
  { value: 'saved_at_desc',      label: 'Recently added'  },
  { value: 'saved_at_asc',       label: 'Oldest first'    },
  { value: 'word_asc',           label: 'Word A→Z'        },
  { value: 'classification_desc', label: 'Hardest first'  },
]

const WEEK_MS = 7 * 24 * 60 * 60 * 1000
const MONTH_MS = 30 * 24 * 60 * 60 * 1000

export default function WordFilterBar({ filters, onChange, sort, onSortChange, isSelecting, onToggleSelecting, hasWords }: Props) {
  const activeClassifications = filters.classification ?? []

  function toggleClassification(cls: WordClassification) {
    const updated = activeClassifications.includes(cls)
      ? activeClassifications.filter((c) => c !== cls)
      : [...activeClassifications, cls]
    onChange({ ...filters, classification: updated })
  }

  function handleSearch(e: React.ChangeEvent<HTMLInputElement>) {
    onChange({ ...filters, search: e.target.value || undefined })
  }

  function toggleDatePreset(preset: 'week' | 'month') {
    if (filters.date_preset === preset) {
      onChange({ ...filters, date_from: undefined, date_preset: undefined })
    } else {
      const ms = preset === 'week' ? WEEK_MS : MONTH_MS
      const date_from = new Date(Date.now() - ms).toISOString()
      onChange({ ...filters, date_from, date_preset: preset })
    }
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        padding: '10px 16px',
        borderBottom: '1px solid var(--color-border)',
        background: 'var(--color-surface)',
      }}
    >
      {/* Row 1: classification pills + search + sort */}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '8px' }}>
        {CLASSIFICATION_FILTERS.map(({ value, label, color }) => {
          const isActive = activeClassifications.includes(value)
          return (
            <button
              key={value}
              onClick={() => toggleClassification(value)}
              aria-pressed={isActive}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                padding: '4px 10px',
                borderRadius: 'var(--radius-full)',
                border: `1.5px solid ${color}`,
                background: isActive ? `color-mix(in srgb, ${color} 12%, transparent)` : 'transparent',
                color: isActive ? color : 'var(--color-text-muted)',
                fontSize: 'var(--text-xs)',
                fontWeight: isActive ? 600 : 400,
                cursor: 'pointer',
                transition: 'all 0.15s',
                minHeight: '30px',
                minWidth: 'unset',
                whiteSpace: 'nowrap',
              }}
            >
              <span
                style={{
                  width: '7px',
                  height: '7px',
                  borderRadius: '50%',
                  background: isActive ? color : 'transparent',
                  border: `1.5px solid ${color}`,
                  flexShrink: 0,
                  transition: 'background 0.15s',
                }}
              />
              {label}
            </button>
          )
        })}

        <div style={{ flex: 1, minWidth: '160px', position: 'relative' }}>
          <span
            aria-hidden="true"
            style={{
              position: 'absolute',
              left: '9px',
              top: '50%',
              transform: 'translateY(-50%)',
              color: 'var(--color-text-muted)',
              pointerEvents: 'none',
              display: 'flex',
            }}
          >
            <IconSearch size={14} />
          </span>
          <input
            role="searchbox"
            type="search"
            placeholder="Search words…"
            value={filters.search ?? ''}
            onChange={handleSearch}
            style={{
              width: '100%',
              paddingLeft: '28px',
              paddingRight: '10px',
              paddingTop: '5px',
              paddingBottom: '5px',
              fontSize: 'var(--text-sm)',
              background: 'var(--color-bg)',
              color: 'var(--color-text)',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-md)',
              outline: 'none',
              minHeight: '32px',
            }}
            onFocus={(e) => (e.currentTarget.style.borderColor = 'var(--color-primary)')}
            onBlur={(e) => (e.currentTarget.style.borderColor = 'var(--color-border)')}
          />
        </div>

        <select
          aria-label="Sort words"
          value={sort}
          onChange={(e) => onSortChange(e.target.value as WordSort)}
          style={{
            fontSize: 'var(--text-xs)',
            padding: '5px 8px',
            background: 'var(--color-bg)',
            color: 'var(--color-text)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-md)',
            cursor: 'pointer',
            outline: 'none',
            minHeight: '32px',
            minWidth: 'unset',
            flexShrink: 0,
          }}
          onFocus={(e) => (e.currentTarget.style.borderColor = 'var(--color-primary)')}
          onBlur={(e) => (e.currentTarget.style.borderColor = 'var(--color-border)')}
        >
          {SORT_OPTIONS.map(({ value, label }) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>

        <button
          onClick={onToggleSelecting}
          disabled={!hasWords}
          aria-pressed={isSelecting}
          style={{
            padding: '5px 12px',
            borderRadius: 'var(--radius-md)',
            border: isSelecting
              ? '1.5px solid var(--color-error)'
              : '1px solid var(--color-border)',
            background: isSelecting
              ? `color-mix(in srgb, var(--color-error) 8%, transparent)`
              : 'transparent',
            color: isSelecting ? 'var(--color-error)' : 'var(--color-text-muted)',
            fontSize: 'var(--text-xs)',
            fontWeight: isSelecting ? 600 : 400,
            cursor: !hasWords ? 'not-allowed' : 'pointer',
            opacity: !hasWords ? 0.4 : 1,
            transition: 'all 0.15s',
            whiteSpace: 'nowrap',
            minHeight: 'unset',
            minWidth: 'unset',
            flexShrink: 0,
          }}
        >
          {isSelecting ? 'Cancel' : 'Delete multiple'}
        </button>
      </div>

      {/* Row 2: date preset chips */}
      <div style={{ display: 'flex', gap: '6px' }}>
        {(['week', 'month'] as const).map((preset) => {
          const label = preset === 'week' ? 'This week' : 'This month'
          const isActive = filters.date_preset === preset
          return (
            <button
              key={preset}
              onClick={() => toggleDatePreset(preset)}
              aria-pressed={isActive}
              style={{
                padding: '3px 10px',
                borderRadius: 'var(--radius-full)',
                border: '1.5px solid var(--color-border)',
                background: isActive ? `color-mix(in srgb, var(--color-primary) 12%, transparent)` : 'transparent',
                color: isActive ? 'var(--color-primary)' : 'var(--color-text-muted)',
                fontSize: 'var(--text-xs)',
                fontWeight: isActive ? 600 : 400,
                cursor: 'pointer',
                transition: 'all 0.15s',
                minHeight: 'unset',
                minWidth: 'unset',
                whiteSpace: 'nowrap',
              }}
            >
              {label}
            </button>
          )
        })}
      </div>
    </div>
  )
}
