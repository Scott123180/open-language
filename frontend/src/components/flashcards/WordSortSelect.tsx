import type { WordSort } from '../../services/flashcardsApi'
import ThemedSelect from '../shared/ThemedSelect'
import { sortSelectStyle } from './wordFilterStyles'

const SORT_OPTIONS: { value: WordSort; label: string }[] = [
  { value: 'saved_at_desc', label: 'Recently added' },
  { value: 'saved_at_asc', label: 'Oldest first' },
  { value: 'word_asc', label: 'Word A→Z' },
  { value: 'classification_desc', label: 'Hardest first' },
]

interface WordSortSelectProps {
  sort: WordSort
  onSortChange: (sort: WordSort) => void
}

/** How the word list is ordered. */
export default function WordSortSelect({ sort, onSortChange }: WordSortSelectProps) {
  return (
    <ThemedSelect label="Sort words" value={sort} options={SORT_OPTIONS} onChange={(value) => onSortChange(value as WordSort)}
      style={sortSelectStyle} isCompact />
  )
}
