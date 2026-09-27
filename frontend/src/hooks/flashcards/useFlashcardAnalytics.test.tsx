import type { ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as api from '../../services/api'
import * as flashcardsApi from '../../services/flashcardsApi'
import { useFlashcardAnalytics } from './useFlashcardAnalytics'

vi.mock('../../services/api')
vi.mock('../../services/flashcardsApi')

const languages = [{ language_id: 'de', display_name: 'German' }] as api.PracticeLanguageOption[]

function wrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return {
    client,
    wrapper: ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    ),
  }
}

describe('useFlashcardAnalytics', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.getPracticeLanguages).mockResolvedValue(languages)
    vi.mocked(api.getSettings).mockResolvedValue({ target_language: 'de' } as api.AppSettings)
    vi.mocked(flashcardsApi.fetchAnalytics).mockResolvedValue({} as flashcardsApi.AnalyticsSummary)
  })

  it('asks for the practice language\'s figures', async () => {
    const { wrapper: Wrapper } = wrapper()

    renderHook(() => useFlashcardAnalytics('30d'), { wrapper: Wrapper })

    await waitFor(() => expect(flashcardsApi.fetchAnalytics).toHaveBeenCalledWith('de', '30d'))
  })

  it('keys the cache by the language', async () => {
    const { client, wrapper: Wrapper } = wrapper()

    renderHook(() => useFlashcardAnalytics('all'), { wrapper: Wrapper })

    await waitFor(() => expect(flashcardsApi.fetchAnalytics).toHaveBeenCalled())
    expect(client.getQueryCache().find({ queryKey: ['analytics', 'de', 'all'] })).toBeDefined()
  })

  it('does not fetch until the language is known', () => {
    vi.mocked(api.getPracticeLanguages).mockReturnValue(new Promise(() => {}))
    const { wrapper: Wrapper } = wrapper()

    const { result } = renderHook(() => useFlashcardAnalytics('all'), { wrapper: Wrapper })

    expect(flashcardsApi.fetchAnalytics).not.toHaveBeenCalled()
    expect(result.current.isLoading).toBe(true)
  })
})
