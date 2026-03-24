import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import CardAnswer from './CardAnswer'
import * as api from '../../services/flashcardsApi'

vi.mock('../../services/flashcardsApi', () => ({
  fetchWordInfo: vi.fn(),
}))

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe('CardAnswer', () => {
  it('is hidden before flip', () => {
    render(
      <CardAnswer vocabularyItemId={1} isFlipped={false} />,
      { wrapper },
    )
    expect(screen.queryByRole('button', { name: /all meanings/i })).not.toBeInTheDocument()
  })

  it('shows all 4 info buttons after flip', () => {
    render(
      <CardAnswer vocabularyItemId={1} isFlipped={true} />,
      { wrapper },
    )
    expect(screen.getByRole('button', { name: /all meanings/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /usage/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /phrases/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /similar/i })).toBeInTheDocument()
  })

  it('shows loading state while fetching', async () => {
    vi.mocked(api.fetchWordInfo).mockReturnValue(new Promise(() => {}))
    render(
      <CardAnswer vocabularyItemId={1} isFlipped={true} />,
      { wrapper },
    )
    screen.getByRole('button', { name: /all meanings/i }).click()
    await waitFor(() => {
      expect(screen.getByText(/loading/i)).toBeInTheDocument()
    })
  })

  it('renders fetched content after load', async () => {
    vi.mocked(api.fetchWordInfo).mockResolvedValue({
      vocabulary_item_id: 1,
      cache_type: 'meanings',
      content: 'Bonjour: hello in French',
      from_cache: false,
      generated_at: new Date().toISOString(),
    })
    render(
      <CardAnswer vocabularyItemId={1} isFlipped={true} />,
      { wrapper },
    )
    screen.getByRole('button', { name: /all meanings/i }).click()
    await waitFor(() => {
      expect(screen.getByText('Bonjour: hello in French')).toBeInTheDocument()
    })
  })
})
