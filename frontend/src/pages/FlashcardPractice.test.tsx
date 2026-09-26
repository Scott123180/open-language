import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import FlashcardPractice from './FlashcardPractice'
import * as api from '../services/flashcardsApi'

vi.mock('../services/flashcardsApi')

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => ({
  ...(await vi.importActual<typeof import('react-router-dom')>('react-router-dom')),
  useNavigate: () => mockNavigate,
}))

const SESSION_ID = 5
const DECK_ID = 3

const card = (position: number, word: string): api.DeckCardItem => ({
  position,
  vocabulary_item_id: 100 + position,
  word,
  translation: `${word}-en`,
  fill_blank_sentence: null,
})

const deck = (cards: api.DeckCardItem[]): api.DeckDetail => ({
  id: DECK_ID,
  name: 'Travel words',
  practice_mode: 'recall',
  algorithm: 'mixed_review',
  requested_size: cards.length,
  actual_size: cards.length,
  size_adjusted: false,
  created_at: '2026-03-20T10:00:00Z',
  cards,
})

const twoCards = deck([card(0, 'bonjour'), card(1, 'merci')])

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/flashcards/practice/${SESSION_ID}`]}>
        <Routes>
          <Route path="/flashcards/practice/:sessionId" element={children} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

const renderPage = () => render(<FlashcardPractice />, { wrapper })

/** The deck id is read from the real query string, not from router state. */
const setDeckIdInUrl = (deckId: number | null) =>
  window.history.replaceState({}, '', deckId == null ? '/' : `/?deck_id=${deckId}`)

const flip = () => fireEvent.click(screen.getByRole('button', { name: 'Flip card' }))
const rate = (label: string) => fireEvent.click(screen.getByRole('button', { name: label }))

beforeEach(() => {
  vi.clearAllMocks()
  setDeckIdInUrl(DECK_ID)
  vi.mocked(api.getDeck).mockResolvedValue(twoCards)
  vi.mocked(api.recordCardResult).mockResolvedValue({} as never)
  vi.mocked(api.endSession).mockResolvedValue({} as never)
  vi.mocked(api.getVocabTtsUrl).mockImplementation((id) => `/api/flashcards/tts/${id}`)
  vi.mocked(api.fetchWordInfo).mockResolvedValue({ content: 'a greeting', cached: true } as never)
})

describe('FlashcardPractice — loading and empty states', () => {
  it('shows a loading message while the deck is in flight', () => {
    vi.mocked(api.getDeck).mockReturnValue(new Promise(() => {}))

    renderPage()

    expect(screen.getByText('Loading…')).toBeInTheDocument()
  })

  it('reports when the deck has no cards', async () => {
    vi.mocked(api.getDeck).mockResolvedValue(deck([]))

    renderPage()

    expect(await screen.findByText('No cards available.')).toBeInTheDocument()
  })

  it('reports when no deck id is present in the url', async () => {
    setDeckIdInUrl(null)

    renderPage()

    expect(await screen.findByText('No cards available.')).toBeInTheDocument()
    expect(api.getDeck).not.toHaveBeenCalled()
  })
})

describe('FlashcardPractice — card progression', () => {
  it('shows the first card and the running count', async () => {
    renderPage()

    expect(await screen.findByText('bonjour')).toBeInTheDocument()
    expect(screen.getByText('Card 1 of 2')).toBeInTheDocument()
  })

  it('hides the rating bar until the card is flipped', async () => {
    renderPage()
    await screen.findByText('bonjour')

    expect(screen.queryByRole('button', { name: 'Knew It' })).not.toBeInTheDocument()

    flip()

    expect(await screen.findByRole('button', { name: 'Knew It' })).toBeInTheDocument()
  })

  it('records the rating and advances to the next card', async () => {
    renderPage()
    await screen.findByText('bonjour')
    flip()

    rate('Knew It')

    await waitFor(() =>
      expect(api.recordCardResult).toHaveBeenCalledWith(SESSION_ID, 0, 'knew_it')
    )
    expect(await screen.findByText('Card 2 of 2')).toBeInTheDocument()
    expect(screen.getByText('merci')).toBeInTheDocument()
  })

  it('resets the flip state on the next card', async () => {
    renderPage()
    await screen.findByText('bonjour')
    flip()
    rate('Guessed')

    await screen.findByText('Card 2 of 2')

    expect(screen.queryByRole('button', { name: 'Knew It' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Flip card' })).toBeInTheDocument()
  })

  it('passes the chosen rating through unchanged', async () => {
    renderPage()
    await screen.findByText('bonjour')
    flip()

    rate("Didn't Know")

    await waitFor(() =>
      expect(api.recordCardResult).toHaveBeenCalledWith(SESSION_ID, 0, 'didnt_know')
    )
  })
})

describe('FlashcardPractice — finishing the session', () => {
  it('ends the session and opens the summary after the last card', async () => {
    vi.mocked(api.getDeck).mockResolvedValue(deck([card(0, 'bonjour')]))
    renderPage()
    await screen.findByText('bonjour')
    flip()

    rate('Knew It')

    await waitFor(() => expect(api.endSession).toHaveBeenCalledWith(SESSION_ID, true))
    expect(mockNavigate).toHaveBeenCalledWith(`/flashcards/summary/${SESSION_ID}`)
  })

  it('does not end the session while cards remain', async () => {
    renderPage()
    await screen.findByText('bonjour')
    flip()

    rate('Knew It')

    await screen.findByText('Card 2 of 2')
    expect(api.endSession).not.toHaveBeenCalled()
  })

  it('marks the session incomplete when the learner exits early', async () => {
    renderPage()
    await screen.findByText('bonjour')

    fireEvent.click(screen.getByRole('button', { name: 'Exit' }))

    await waitFor(() => expect(api.endSession).toHaveBeenCalledWith(SESSION_ID, false))
    expect(mockNavigate).toHaveBeenCalledWith(`/flashcards/summary/${SESSION_ID}`)
  })

  it('still leaves the session when ending it fails on exit', async () => {
    vi.mocked(api.endSession).mockRejectedValue(new Error('offline'))
    renderPage()
    await screen.findByText('bonjour')

    fireEvent.click(screen.getByRole('button', { name: 'Exit' }))

    await waitFor(() =>
      expect(mockNavigate).toHaveBeenCalledWith(`/flashcards/summary/${SESSION_ID}`)
    )
  })
})

describe('FlashcardPractice — rating failures', () => {
  it('surfaces the server message and keeps the learner on the card', async () => {
    vi.mocked(api.recordCardResult).mockRejectedValue(new Error('Session already ended'))
    renderPage()
    await screen.findByText('bonjour')
    flip()

    rate('Knew It')

    expect(await screen.findByText('Session already ended')).toBeInTheDocument()
    expect(screen.getByText('Card 1 of 2')).toBeInTheDocument()
  })

  it('falls back to a generic message for a non-Error rejection', async () => {
    vi.mocked(api.recordCardResult).mockRejectedValue('nope')
    renderPage()
    await screen.findByText('bonjour')
    flip()

    rate('Knew It')

    expect(await screen.findByText('Failed to record rating')).toBeInTheDocument()
  })

  it('dismisses the error banner', async () => {
    vi.mocked(api.recordCardResult).mockRejectedValue(new Error('Session already ended'))
    renderPage()
    await screen.findByText('bonjour')
    flip()
    rate('Knew It')
    await screen.findByText('Session already ended')

    fireEvent.click(screen.getByRole('button', { name: /dismiss/i }))

    await waitFor(() =>
      expect(screen.queryByText('Session already ended')).not.toBeInTheDocument()
    )
  })
})

describe('FlashcardPractice — audio', () => {
  it('offers audio for a card backed by a vocabulary item', async () => {
    renderPage()
    await screen.findByText('bonjour')

    expect(api.getVocabTtsUrl).toHaveBeenCalledWith(100)
  })

  it('renders no audio controls for a card with no vocabulary item', async () => {
    vi.mocked(api.getDeck).mockResolvedValue(
      deck([{ ...card(0, 'bonjour'), vocabulary_item_id: null }])
    )

    renderPage()
    await screen.findByText('bonjour')

    expect(api.getVocabTtsUrl).not.toHaveBeenCalled()
  })
})
