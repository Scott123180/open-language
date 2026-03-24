import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import FlashcardSummary from './FlashcardSummary'
import * as api from '../services/flashcardsApi'

vi.mock('../services/flashcardsApi', () => ({
  getSessionSummary: vi.fn(),
  getEncouragement: vi.fn(),
  createMissedDeck: vi.fn(),
}))

const mockSummary = {
  session_id: 1,
  completed: true,
  cards_reviewed: 3,
  total_cards: 3,
  knew_it_count: 2,
  guessed_count: 1,
  didnt_know_count: 0,
  duration_seconds: 90,
  current_streak: 5,
  words_needing_work: [
    { id: 2, word: 'merci', translation: 'thank you', rating: 'guessed' },
  ],
}

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/flashcards/summary/1']}>
        <Routes>
          <Route path="/flashcards/summary/:sessionId" element={children} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('FlashcardSummary', () => {
  beforeEach(() => {
    vi.mocked(api.getSessionSummary).mockResolvedValue(mockSummary)
    vi.mocked(api.getEncouragement).mockResolvedValue({ message: 'Great job!' })
  })

  it('shows Session Complete heading', async () => {
    render(<FlashcardSummary />, { wrapper })
    expect(await screen.findByRole('heading', { name: /session complete/i })).toBeInTheDocument()
  })

  it('shows knew it count', async () => {
    render(<FlashcardSummary />, { wrapper })
    await screen.findByRole('heading', { name: /session complete/i })
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  it('shows words needing work list', async () => {
    render(<FlashcardSummary />, { wrapper })
    expect(await screen.findByText('merci')).toBeInTheDocument()
  })

  it('shows streak indicator', async () => {
    render(<FlashcardSummary />, { wrapper })
    expect(await screen.findByText(/5-day streak/i)).toBeInTheDocument()
  })

  it('has Back to Decks button', async () => {
    render(<FlashcardSummary />, { wrapper })
    expect(await screen.findByRole('button', { name: /back to decks/i })).toBeInTheDocument()
  })

  it('has Back to Word List button', async () => {
    render(<FlashcardSummary />, { wrapper })
    expect(await screen.findByRole('button', { name: /back to word list/i })).toBeInTheDocument()
  })

  it('has Practice Again button', async () => {
    render(<FlashcardSummary />, { wrapper })
    expect(await screen.findByRole('button', { name: /practice again/i })).toBeInTheDocument()
  })

  it('has Practice Missed Words button', async () => {
    render(<FlashcardSummary />, { wrapper })
    expect(await screen.findByRole('button', { name: /practice missed/i })).toBeInTheDocument()
  })
})
