import type { ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as api from '../../services/api'
import * as flashcardsApi from '../../services/flashcardsApi'
import { useDecks } from './useDecks'

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

describe('useDecks', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.getPracticeLanguages).mockResolvedValue(languages)
    vi.mocked(api.getSettings).mockResolvedValue({ target_language: 'de' } as api.AppSettings)
    vi.mocked(flashcardsApi.listDecks).mockResolvedValue([])
  })

  it('asks for the practice language\'s decks', async () => {
    const { wrapper: Wrapper } = wrapper()

    renderHook(() => useDecks(), { wrapper: Wrapper })

    await waitFor(() => expect(flashcardsApi.listDecks).toHaveBeenCalledWith('de'))
  })

  it('keys the cache by the language', async () => {
    const { client, wrapper: Wrapper } = wrapper()

    renderHook(() => useDecks(), { wrapper: Wrapper })

    await waitFor(() => expect(flashcardsApi.listDecks).toHaveBeenCalled())
    expect(client.getQueryCache().find({ queryKey: ['flashcard-decks', 'de'] })).toBeDefined()
  })

  it('does not fetch until the language is known', () => {
    vi.mocked(api.getPracticeLanguages).mockReturnValue(new Promise(() => {}))
    const { wrapper: Wrapper } = wrapper()

    const { result } = renderHook(() => useDecks(), { wrapper: Wrapper })

    expect(flashcardsApi.listDecks).not.toHaveBeenCalled()
    expect(result.current.isLoading).toBe(true)
  })
})
