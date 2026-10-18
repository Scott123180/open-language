import type { WordFilters } from '../../services/flashcardsApi'
import { chipStyle } from './wordFilterStyles'

const WEEK_MS = 7 * 24 * 60 * 60 * 1000
const MONTH_MS = 30 * 24 * 60 * 60 * 1000
const PRESETS = [
  { preset: 'week', label: 'This week', ms: WEEK_MS },
  { preset: 'month', label: 'This month', ms: MONTH_MS },
] as const

interface DatePresetChipsProps {
  filters: WordFilters
  onChange: (filters: WordFilters) => void
}

/** "This week" and "This month": pressing the active one again clears the date filter. */
export default function DatePresetChips({ filters, onChange }: DatePresetChipsProps) {
  const toggle = (preset: 'week' | 'month', ms: number) =>
    onChange(
      filters.date_preset === preset
        ? { ...filters, date_from: undefined, date_preset: undefined }
        : { ...filters, date_from: new Date(Date.now() - ms).toISOString(), date_preset: preset },
    )
  return (
    <div style={{ display: 'flex', gap: '6px' }}>
      {PRESETS.map(({ preset, label, ms }) => (
        <button key={preset} onClick={() => toggle(preset, ms)} aria-pressed={filters.date_preset === preset} style={chipStyle(filters.date_preset === preset)}>
          {label}
        </button>
      ))}
    </div>
  )
}
