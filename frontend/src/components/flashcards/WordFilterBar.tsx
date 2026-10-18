import type { WordFilters, WordSort } from '../../services/flashcardsApi'
import { IconSearch } from '../shared/icons'
import ClassificationPills from './ClassificationPills'
import DatePresetChips from './DatePresetChips'
import WordSortSelect from './WordSortSelect'
import { barStyle, rowStyle, searchIconStyle, searchInputStyle, searchWrapperStyle, selectToggleStyle } from './wordFilterStyles'

interface Props {
  filters: WordFilters
  onChange: (filters: WordFilters) => void
  sort: WordSort
  onSortChange: (sort: WordSort) => void
  isSelecting: boolean
  onToggleSelecting: () => void
  hasWords: boolean
}

/** Filter and order the saved words: classifications, a search, the sort and date presets. */
export default function WordFilterBar({ filters, onChange, sort, onSortChange, isSelecting, onToggleSelecting, hasWords }: Props) {
  return (
    <div style={barStyle}>
      <div style={rowStyle}>
        <ClassificationPills active={filters.classification ?? []} onChange={(classification) => onChange({ ...filters, classification })} />
        <WordSearch value={filters.search ?? ''} onChange={(search) => onChange({ ...filters, search: search || undefined })} />
        <WordSortSelect sort={sort} onSortChange={onSortChange} />
        <button onClick={onToggleSelecting} disabled={!hasWords} aria-pressed={isSelecting} style={selectToggleStyle(isSelecting, hasWords)}>
          {isSelecting ? 'Cancel' : 'Delete multiple'}
        </button>
      </div>
      <DatePresetChips filters={filters} onChange={onChange} />
    </div>
  )
}

function WordSearch({ value, onChange }: { value: string; onChange: (search: string) => void }) {
  return (
    <div style={searchWrapperStyle}>
      <span aria-hidden="true" style={searchIconStyle}><IconSearch size={14} /></span>
      <input role="searchbox" type="search" placeholder="Search words…" value={value} onChange={(e) => onChange(e.target.value)} style={searchInputStyle}
        onFocus={(e) => (e.currentTarget.style.borderColor = 'var(--color-primary)')}
        onBlur={(e) => (e.currentTarget.style.borderColor = 'var(--color-border)')} />
    </div>
  )
}
