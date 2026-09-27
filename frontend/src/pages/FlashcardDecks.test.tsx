import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import FlashcardDecks from './FlashcardDecks'
import * as api from '../services/flashcardsApi'

vi.mock('../services/flashcardsApi')
// The Flashcards screens show the practice language's data; Spanish here.
vi.mock('../hooks/usePracticeLanguages', () => ({
  usePracticeLanguages: () => ({
    current: { language_id: 'es', display_name: 'Spanish' },
    languages: [],
    nameOf: (id: string) => id,
    isLoading: false,
    error: null,
  }),
}))

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => ({
  ...(await vi.importActual<typeof import('react-router-dom')>('react-router-dom')),
  useNavigate: () => mockNavigate,
}))

// DeckConfigPanel is exercised by its own suite; stub it to a single button so
// these tests stay about the decks page.
vi.mock('../components/flashcards/DeckConfigPanel', () => ({
  default: ({ onCreated }: { onCreated: (deck: { id: number }) => void }) => (
    <button onClick={() => onCreated({ id: 99 })}>stub-create</button>
  ),
}))

const deck = (over: Partial<api.DeckSummary> = {}): api.DeckSummary => ({
  id: 1,
  name: 'Travel words',
  practice_mode: 'recall',
  algorithm: 'mixed_review',
  card_count: 12,
  created_at: '2026-03-20T10:00:00Z',
  target_language: 'es',
  last_practiced_at: null,
  session_count: 0,
  last_accuracy: null,
  ...over,
})

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}

const renderPage = () => render(<FlashcardDecks />, { wrapper })

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(api.listDecks).mockResolvedValue([deck()])
  vi.mocked(api.deleteDeck).mockResolvedValue(undefined)
  vi.mocked(api.startSession).mockResolvedValue({
    id: 42,
    deck_id: 1,
    practice_mode: 'recall',
  } as never)
})

describe('FlashcardDecks — loading and empty states', () => {
  it('announces loading while decks are in flight', () => {
    vi.mocked(api.listDecks).mockReturnValue(new Promise(() => {}))

    renderPage()

    expect(screen.getByText('Loading decks…')).toBeInTheDocument()
  })

  it('invites the learner to create a deck when there are none', async () => {
    vi.mocked(api.listDecks).mockResolvedValue([])

    renderPage()

    expect(
      await screen.findByText('No decks yet. Create one to start practicing.')
    ).toBeInTheDocument()
  })
})

describe('FlashcardDecks — deck cards', () => {
  it('labels a deck by its mode and algorithm', async () => {
    renderPage()

    expect(await screen.findByText('Recall · Mixed Review')).toBeInTheDocument()
  })

  it('maps every practice mode and algorithm to a label', async () => {
    vi.mocked(api.listDecks).mockResolvedValue([
      deck({ id: 1, practice_mode: 'listen', algorithm: 'not_practiced' }),
      deck({ id: 2, practice_mode: 'produce', algorithm: 'difficult' }),
      deck({ id: 3, practice_mode: 'fill_blank', algorithm: 'previously_guessed' }),
    ])

    renderPage()

    expect(await screen.findByText('Listen · New Words')).toBeInTheDocument()
    expect(screen.getByText('Produce · Difficult')).toBeInTheDocument()
    expect(screen.getByText('Fill in the Blank · Almost Learned')).toBeInTheDocument()
  })

  it('marks a never-practised deck as New and dates it by creation', async () => {
    renderPage()
    await screen.findByText('Recall · Mixed Review')

    expect(screen.getByText('New')).toBeInTheDocument()
    expect(screen.getByText(/12 cards · created/)).toBeInTheDocument()
  })

  it('drops the New badge and dates by last practice once practised', async () => {
    vi.mocked(api.listDecks).mockResolvedValue([
      deck({ session_count: 3, last_practiced_at: '2026-03-25T10:00:00Z' }),
    ])

    renderPage()
    await screen.findByText('Recall · Mixed Review')

    expect(screen.queryByText('New')).not.toBeInTheDocument()
    expect(screen.getByText(/12 cards · /)).toBeInTheDocument()
  })

  it('shows the last accuracy as a percentage', async () => {
    vi.mocked(api.listDecks).mockResolvedValue([
      deck({ session_count: 2, last_accuracy: 0.83 }),
    ])

    renderPage()

    expect(await screen.findByText('83%')).toBeInTheDocument()
  })

  it.each([
    [0.95, '95%'],
    [0.7, '70%'],
    [0.3, '30%'],
  ])('colours the accuracy bar for %s', async (accuracy, shown) => {
    vi.mocked(api.listDecks).mockResolvedValue([
      deck({ session_count: 2, last_accuracy: accuracy }),
    ])

    renderPage()

    expect(await screen.findByText(shown)).toBeInTheDocument()
  })

  it('omits the accuracy bar when there is no recorded accuracy', async () => {
    renderPage()
    await screen.findByText('Recall · Mixed Review')

    expect(screen.queryByText('%', { exact: false })).not.toBeInTheDocument()
  })

  it('includes the year for a deck created in an earlier year', async () => {
    vi.mocked(api.listDecks).mockResolvedValue([deck({ created_at: '2020-01-15T10:00:00Z' })])

    renderPage()

    expect(await screen.findByText(/2020/)).toBeInTheDocument()
  })
})

describe('FlashcardDecks — starting practice', () => {
  it('starts a session and opens practice with the deck id in the query', async () => {
    renderPage()
    const start = await screen.findByRole('button', { name: 'Start practice for Travel words' })

    fireEvent.click(start)

    await waitFor(() => expect(api.startSession).toHaveBeenCalledWith(1, expect.anything()))
    expect(mockNavigate).toHaveBeenCalledWith('/flashcards/practice/42?deck_id=1')
  })

  it('surfaces a failure to start', async () => {
    vi.mocked(api.startSession).mockRejectedValue(new Error('Deck is empty'))
    renderPage()

    fireEvent.click(await screen.findByRole('button', { name: 'Start practice for Travel words' }))

    expect(await screen.findByText('Deck is empty')).toBeInTheDocument()
    expect(mockNavigate).not.toHaveBeenCalled()
  })
})

describe('FlashcardDecks — deleting', () => {
  it('deletes the deck', async () => {
    renderPage()

    fireEvent.click(await screen.findByRole('button', { name: 'Delete deck Travel words' }))

    await waitFor(() => expect(api.deleteDeck).toHaveBeenCalledWith(1, expect.anything()))
  })

  it('surfaces a failure to delete and lets it be dismissed', async () => {
    vi.mocked(api.deleteDeck).mockRejectedValue(new Error('Deck in use'))
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: 'Delete deck Travel words' }))
    await screen.findByText('Deck in use')

    fireEvent.click(screen.getByRole('button', { name: /dismiss/i }))

    await waitFor(() => expect(screen.queryByText('Deck in use')).not.toBeInTheDocument())
  })
})

describe('FlashcardDecks — create panel', () => {
  it('is closed until New Deck is pressed', async () => {
    renderPage()
    await screen.findByText('Recall · Mixed Review')

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'New Deck' }))

    expect(screen.getByRole('dialog', { name: 'Create new deck' })).toBeInTheDocument()
  })

  it('toggles shut when New Deck is pressed again', async () => {
    renderPage()
    await screen.findByText('Recall · Mixed Review')
    fireEvent.click(screen.getByRole('button', { name: 'New Deck' }))

    fireEvent.click(screen.getByRole('button', { name: 'New Deck' }))

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('closes on the Close button', async () => {
    renderPage()
    await screen.findByText('Recall · Mixed Review')
    fireEvent.click(screen.getByRole('button', { name: 'New Deck' }))

    fireEvent.click(screen.getByRole('button', { name: 'Close' }))

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('closes on Escape', async () => {
    renderPage()
    await screen.findByText('Recall · Mixed Review')
    fireEvent.click(screen.getByRole('button', { name: 'New Deck' }))

    fireEvent.keyDown(document, { key: 'Escape' })

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  })

  it('closes the panel and refreshes the list once a deck is created', async () => {
    renderPage()
    await screen.findByText('Recall · Mixed Review')
    fireEvent.click(screen.getByRole('button', { name: 'New Deck' }))

    fireEvent.click(screen.getByRole('button', { name: 'stub-create' }))

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(mockNavigate).toHaveBeenCalledWith('/flashcards/decks')
  })

  it('closes the panel when the config panel is cancelled', async () => {
    renderPage()
    await screen.findByText('Recall · Mixed Review')
    fireEvent.click(screen.getByRole('button', { name: 'New Deck' }))

    fireEvent.keyDown(document, { key: 'Escape' })

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  })

  it('ignores other keys', async () => {
    renderPage()
    await screen.findByText('Recall · Mixed Review')
    fireEvent.click(screen.getByRole('button', { name: 'New Deck' }))

    fireEvent.keyDown(document, { key: 'a' })

    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })
})

describe('FlashcardDecks — navigation', () => {
  it('goes back to the word list', async () => {
    renderPage()
    await screen.findByText('Recall · Mixed Review')

    fireEvent.click(screen.getByRole('button', { name: 'Words' }))

    expect(mockNavigate).toHaveBeenCalledWith('/flashcards')
  })
})
