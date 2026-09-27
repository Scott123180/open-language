import * as api from '../../services/flashcardsApi'
import { useLanguageQuery } from './useLanguageQuery'

/** The practice language's saved words, filtered. */
export function useWordLibrary(filters: api.WordFilters) {
  return useLanguageQuery(['flashcard-words', filters], (language) =>
    api.fetchWords(language, filters),
  )
}
