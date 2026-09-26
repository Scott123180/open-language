import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import FlashcardSummary from './FlashcardSummary'
import * as api from '../services/flashcardsApi'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => ({
  ...(await vi.importActual<typeof import('react-router-dom')>('react-router-dom')),
  useNavigate: () => mockNavigate,
}))

vi.mock('../services/flashcardsApi', () => ({
  getSessionSummary: vi.fn(),
  getEncouragement: vi.fn(),
  createMissedDeck: vi.fn(),
  startSession: vi.fn(),
}))

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(api.getEncouragement).mockResolvedValue({ message: 'Great job!' })
})

const mockSummary: api.SessionSummary = {
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

describe('FlashcardSummary — loading and failure', () => {
  it('shows a loading message while the summary is in flight', () => {
    vi.mocked(api.getSessionSummary).mockReturnValue(new Promise(() => {}))

    render(<FlashcardSummary />, { wrapper })

    expect(screen.getByText('Loading summary…')).toBeInTheDocument()
  })

  it('offers a way out when the summary fails to load', async () => {
    vi.mocked(api.getSessionSummary).mockRejectedValue(new Error('boom'))

    render(<FlashcardSummary />, { wrapper })
    await screen.findByText('Failed to load session summary.')

    fireEvent.click(screen.getByRole('button', { name: /dismiss/i }))

    expect(mockNavigate).toHaveBeenCalledWith('/flashcards/decks')
  })
})

describe('FlashcardSummary — figures', () => {
  it('notes when the learner exited early', async () => {
    vi.mocked(api.getSessionSummary).mockResolvedValue({ ...mockSummary, completed: false })

    render(<FlashcardSummary />, { wrapper })

    expect(await screen.findByText(/exited early/)).toBeInTheDocument()
  })

  it('formats a sub-minute duration in seconds', async () => {
    vi.mocked(api.getSessionSummary).mockResolvedValue({ ...mockSummary, duration_seconds: 45 })

    render(<FlashcardSummary />, { wrapper })

    expect(await screen.findByText(/45s/)).toBeInTheDocument()
  })

  it('formats a longer duration in minutes and seconds', async () => {
    vi.mocked(api.getSessionSummary).mockResolvedValue({ ...mockSummary, duration_seconds: 90 })

    render(<FlashcardSummary />, { wrapper })

    expect(await screen.findByText(/1m 30s/)).toBeInTheDocument()
  })

  it('shows a dash when the duration is unknown', async () => {
    vi.mocked(api.getSessionSummary).mockResolvedValue({
      ...mockSummary,
      duration_seconds: null as unknown as number,
    })

    render(<FlashcardSummary />, { wrapper })

    expect(await screen.findByText(/—/)).toBeInTheDocument()
  })

  it('reports zero percent rather than dividing by zero', async () => {
    vi.mocked(api.getSessionSummary).mockResolvedValue({
      ...mockSummary,
      cards_reviewed: 0,
      knew_it_count: 0,
      guessed_count: 0,
      didnt_know_count: 0,
    })

    render(<FlashcardSummary />, { wrapper })

    expect(await screen.findByText(/Knew It \(0%\)/)).toBeInTheDocument()
  })

  it('hides the needs-work list when there is nothing to review', async () => {
    vi.mocked(api.getSessionSummary).mockResolvedValue({ ...mockSummary, words_needing_work: [] })

    render(<FlashcardSummary />, { wrapper })
    await screen.findByRole('heading', { name: /session complete/i })

    expect(screen.queryByText('merci')).not.toBeInTheDocument()
  })
})

describe('FlashcardSummary — actions', () => {
  beforeEach(() => {
    vi.mocked(api.getSessionSummary).mockResolvedValue(mockSummary)
  })

  it.each([
    ['Back to Decks', '/flashcards/decks'],
    ['Practice Again', '/flashcards/decks'],
  ])('navigates from %s', async (name, path) => {
    render(<FlashcardSummary />, { wrapper })
    await screen.findByRole('heading', { name: /session complete/i })

    fireEvent.click(screen.getByRole('button', { name }))

    expect(mockNavigate).toHaveBeenCalledWith(path)
  })

  it('builds a deck of missed words and starts practising it', async () => {
    vi.mocked(api.createMissedDeck).mockResolvedValue({ id: 9 } as api.DeckDetail)
    vi.mocked(api.startSession).mockResolvedValue({ id: 21 } as never)
    render(<FlashcardSummary />, { wrapper })
    await screen.findByRole('heading', { name: /session complete/i })

    fireEvent.click(screen.getByRole('button', { name: 'Practice Missed Words' }))

    await waitFor(() => expect(api.createMissedDeck).toHaveBeenCalledWith(1))
    expect(mockNavigate).toHaveBeenCalledWith('/flashcards/practice/21?deck_id=9')
  })

  it('stays put when there are no missed words to build a deck from', async () => {
    vi.mocked(api.createMissedDeck).mockRejectedValue(new Error('no missed words'))
    render(<FlashcardSummary />, { wrapper })
    await screen.findByRole('heading', { name: /session complete/i })

    fireEvent.click(screen.getByRole('button', { name: 'Practice Missed Words' }))

    await waitFor(() => expect(api.createMissedDeck).toHaveBeenCalled())
    expect(mockNavigate).not.toHaveBeenCalled()
  })
})
