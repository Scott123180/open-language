import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import FlashcardAnalytics from './FlashcardAnalytics'
import * as api from '../services/flashcardsApi'

vi.mock('../services/flashcardsApi')

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => ({
  ...(await vi.importActual<typeof import('react-router-dom')>('react-router-dom')),
  useNavigate: () => mockNavigate,
}))

// Recharts measures its container via ResizeObserver, which jsdom lacks.
vi.stubGlobal(
  'ResizeObserver',
  class {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
)

const summary: api.AnalyticsSummary = {
  at_a_glance: {
    total_words: 120,
    words_learned: 45,
    current_streak: 6,
    sessions_this_week: 4,
  },
  accuracy_trend: [{ session_id: 1, date: '2026-03-20', accuracy: 0.8 }],
  daily_activity: [{ date: '2026-03-20', cards_reviewed: 10 }],
  classification_over_time: [
    { date: '2026-03-20', not_practiced: 5, difficult: 3, almost_learned: 2, learned: 1 },
  ],
  classification_now: { not_practiced: 5, difficult: 3, almost_learned: 2, learned: 1 },
  hardest_words: [
    { id: 7, word: 'sobremesa', encounters: 9, success_rate: 0.22 },
    { id: 8, word: 'madrugar', encounters: 6, success_rate: 0.75 },
  ],
  recently_learned: [{ id: 9, word: 'bonjour', learned_at: '2026-03-21T10:00:00Z' }],
  mode_performance: [{ mode: 'recall', accuracy: 82 }],
}

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}

const renderPage = () => render(<FlashcardAnalytics />, { wrapper })

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(api.fetchAnalytics).mockResolvedValue(summary)
})

describe('FlashcardAnalytics — loading and failure', () => {
  it('shows a loading message while the summary is in flight', () => {
    vi.mocked(api.fetchAnalytics).mockReturnValue(new Promise(() => {}))

    renderPage()

    expect(screen.getByText('Loading analytics…')).toBeInTheDocument()
  })

  it('shows an error banner when the summary fails to load', async () => {
    vi.mocked(api.fetchAnalytics).mockRejectedValue(new Error('boom'))

    renderPage()

    expect(await screen.findByText('Failed to load analytics.')).toBeInTheDocument()
  })

  it('returns to the flashcards page when the error banner is dismissed', async () => {
    vi.mocked(api.fetchAnalytics).mockRejectedValue(new Error('boom'))
    renderPage()
    await screen.findByText('Failed to load analytics.')

    fireEvent.click(screen.getByRole('button', { name: /dismiss/i }))

    expect(mockNavigate).toHaveBeenCalledWith('/flashcards')
  })
})

describe('FlashcardAnalytics — at-a-glance stats', () => {
  it('shows each headline figure with its label', async () => {
    renderPage()
    await screen.findByText('Total Words')

    expect(screen.getByText('120')).toBeInTheDocument()
    expect(screen.getByText('45')).toBeInTheDocument()
    expect(screen.getByText('Words Learned')).toBeInTheDocument()
    expect(screen.getByText('Sessions This Week')).toBeInTheDocument()
  })

  it('renders the streak with a day suffix', async () => {
    renderPage()

    expect(await screen.findByText('6d')).toBeInTheDocument()
  })
})

describe('FlashcardAnalytics — range toggle', () => {
  it('requests the 7-day range first and marks it pressed', async () => {
    renderPage()
    await screen.findByText('Total Words')

    expect(api.fetchAnalytics).toHaveBeenCalledWith('7d')
    expect(screen.getByRole('button', { name: '7 Days' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('refetches with the chosen range and moves the pressed state', async () => {
    renderPage()
    await screen.findByText('Total Words')

    fireEvent.click(screen.getByRole('button', { name: '30 Days' }))

    await waitFor(() => expect(api.fetchAnalytics).toHaveBeenCalledWith('30d'))
    // The new range is a new query key, so the page blanks to its loading state
    // before the buttons come back.
    const thirtyDays = await screen.findByRole('button', { name: '30 Days' })
    expect(thirtyDays).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: '7 Days' })).toHaveAttribute('aria-pressed', 'false')
  })

  it('supports the all-time range', async () => {
    renderPage()
    await screen.findByText('Total Words')

    fireEvent.click(screen.getByRole('button', { name: 'All Time' }))

    await waitFor(() => expect(api.fetchAnalytics).toHaveBeenCalledWith('all'))
  })
})

describe('FlashcardAnalytics — hardest words', () => {
  it('lists each hard word with its encounters and success rate', async () => {
    renderPage()

    expect(await screen.findByText('sobremesa')).toBeInTheDocument()
    expect(screen.getByText('9')).toBeInTheDocument()
    expect(screen.getByText('22%')).toBeInTheDocument()
    expect(screen.getByText('75%')).toBeInTheDocument()
  })

  it('opens the word list filtered to the clicked word', async () => {
    renderPage()
    const row = await screen.findByRole('button', { name: 'View sobremesa in word list' })

    fireEvent.click(row)

    expect(mockNavigate).toHaveBeenCalledWith('/flashcards?word=7')
  })

  it('hides the hardest-words table when there are none', async () => {
    vi.mocked(api.fetchAnalytics).mockResolvedValue({ ...summary, hardest_words: [] })

    renderPage()
    await screen.findByText('Total Words')

    expect(screen.queryByText('Hardest Words')).not.toBeInTheDocument()
  })
})

describe('FlashcardAnalytics — recently learned', () => {
  it('lists recently learned words with a formatted date', async () => {
    renderPage()

    expect(await screen.findByText('bonjour')).toBeInTheDocument()
    expect(screen.getByText('Recently Learned')).toBeInTheDocument()
    expect(
      screen.getByText(new Date('2026-03-21T10:00:00Z').toLocaleDateString())
    ).toBeInTheDocument()
  })

  it('hides the section when nothing has been learned recently', async () => {
    vi.mocked(api.fetchAnalytics).mockResolvedValue({ ...summary, recently_learned: [] })

    renderPage()
    await screen.findByText('Total Words')

    expect(screen.queryByText('Recently Learned')).not.toBeInTheDocument()
  })
})

describe('FlashcardAnalytics — navigation', () => {
  it('goes back to the flashcards page', async () => {
    renderPage()
    const back = await screen.findByRole('button', { name: 'Back to Flashcards' })

    fireEvent.click(back)

    expect(mockNavigate).toHaveBeenCalledWith('/flashcards')
  })

  it('renders every chart section heading', async () => {
    renderPage()
    await screen.findByText('Total Words')

    for (const title of [
      'Accuracy Trend',
      'Daily Activity',
      'Classification Distribution Over Time',
      'Current Classification Breakdown',
      'Performance by Mode',
    ]) {
      expect(screen.getByRole('heading', { name: title })).toBeInTheDocument()
    }
  })
})
