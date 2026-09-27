import * as api from '../../services/flashcardsApi'
import { useLanguageQuery } from './useLanguageQuery'

/** The practice language's decks. */
export function useDecks() {
  return useLanguageQuery(['flashcard-decks'], (language) => api.listDecks(language))
}
