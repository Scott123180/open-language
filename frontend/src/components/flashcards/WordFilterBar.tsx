import type { WordClassification, WordFilters } from '../../services/flashcardsApi'
import { IconSearch } from '../shared/icons'

interface Props {
  filters: WordFilters
  onChange: (filters: WordFilters) => void
}

const FILTERS: { value: WordClassification; label: string; color: string; bg: string }[] = [
  { value: 'not_practiced',  label: 'Not Practiced',  color: '#64748b', bg: 'rgba(100,116,139,0.15)' },
  { value: 'difficult',      label: 'Difficult',      color: '#ef4444', bg: 'rgba(239,68,68,0.12)'   },
  { value: 'almost_learned', label: 'Almost Learned', color: '#f59e0b', bg: 'rgba(245,158,11,0.12)'  },
  { value: 'learned',        label: 'Learned',        color: '#22c55e', bg: 'rgba(34,197,94,0.12)'   },
]

export default function WordFilterBar({ filters, onChange }: Props) {
  const active = filters.classification ?? []

  function toggle(cls: WordClassification) {
    const updated = active.includes(cls)
      ? active.filter((c) => c !== cls)
      : [...active, cls]
    onChange({ ...filters, classification: updated })
  }

  function handleSearch(e: React.ChangeEvent<HTMLInputElement>) {
    onChange({ ...filters, search: e.target.value || undefined })
  }

  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        gap: '8px',
        padding: '10px 16px',
        borderBottom: '1px solid var(--color-border)',
        background: 'var(--color-surface)',
      }}
    >
      {FILTERS.map(({ value, label, color, bg }) => {
        const isActive = active.includes(value)
        return (
          <button
            key={value}
            onClick={() => toggle(value)}
            aria-pressed={isActive}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '5px',
              padding: '4px 10px',
              borderRadius: '999px',
              border: `1.5px solid ${color}`,
              background: isActive ? bg : 'transparent',
              color: isActive ? color : 'var(--color-text-muted)',
              fontSize: '0.78rem',
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
            fontSize: '0.85rem',
            background: 'var(--color-bg)',
            color: 'var(--color-text)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius)',
            outline: 'none',
            minHeight: '32px',
          }}
          onFocus={(e) => (e.currentTarget.style.borderColor = 'var(--color-primary)')}
          onBlur={(e) => (e.currentTarget.style.borderColor = 'var(--color-border)')}
        />
      </div>
    </div>
  )
}
