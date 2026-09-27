import type { ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as api from '../../services/api'
import * as flashcardsApi from '../../services/flashcardsApi'
import { useWordLibrary } from './useWordLibrary'

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

describe('useWordLibrary', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.getPracticeLanguages).mockResolvedValue(languages)
    vi.mocked(api.getSettings).mockResolvedValue({ target_language: 'de' } as api.AppSettings)
    vi.mocked(flashcardsApi.fetchWords).mockResolvedValue([])
  })

  it('asks for the practice language\'s words', async () => {
    const { wrapper: Wrapper } = wrapper()

    renderHook(() => useWordLibrary({ search: 'Haus' }), { wrapper: Wrapper })

    await waitFor(() => expect(flashcardsApi.fetchWords).toHaveBeenCalledWith('de', { search: 'Haus' }))
  })

  it('keys the cache by the language', async () => {
    const { client, wrapper: Wrapper } = wrapper()

    renderHook(() => useWordLibrary({}), { wrapper: Wrapper })

    await waitFor(() => expect(flashcardsApi.fetchWords).toHaveBeenCalled())
    expect(client.getQueryCache().find({ queryKey: ['flashcard-words', 'de', {}] })).toBeDefined()
  })

  it('does not fetch until the language is known', () => {
    vi.mocked(api.getPracticeLanguages).mockReturnValue(new Promise(() => {}))
    const { wrapper: Wrapper } = wrapper()

    const { result } = renderHook(() => useWordLibrary({}), { wrapper: Wrapper })

    expect(flashcardsApi.fetchWords).not.toHaveBeenCalled()
    expect(result.current.isLoading).toBe(true)
  })
})
