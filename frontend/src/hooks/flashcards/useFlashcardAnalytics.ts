import * as api from '../../services/flashcardsApi'
import { useLanguageQuery } from './useLanguageQuery'

/** The practice language's practice statistics for a range. */
export function useFlashcardAnalytics(range: api.AnalyticsRange) {
  return useLanguageQuery(['analytics', range], (language) => api.fetchAnalytics(language, range))
}
