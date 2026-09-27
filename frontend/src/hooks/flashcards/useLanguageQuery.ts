import { useQuery } from '@tanstack/react-query'
import { usePracticeLanguages } from '../usePracticeLanguages'

export interface LanguageQueryResult<T> {
  data: T | undefined
  isLoading: boolean
  error: Error | null
}

/**
 * A flashcards query for the practice language. The language is part of the query key, so a
 * switch never shows the other language's cached data, and nothing is fetched until it is known.
 */
export function useLanguageQuery<T>(
  [name, ...rest]: readonly unknown[],
  fetchFor: (language: string) => Promise<T>,
): LanguageQueryResult<T> {
  const { current, error: languageError } = usePracticeLanguages()
  const language = current?.language_id
  const query = useQuery({
    queryKey: [name, language, ...rest],
    queryFn: () => fetchFor(language as string),
    enabled: Boolean(language),
  })
  if (languageError) return { data: undefined, isLoading: false, error: new Error(languageError) }
  return { data: query.data, isLoading: query.isPending, error: query.error }
}
