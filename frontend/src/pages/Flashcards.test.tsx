import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Flashcards from './Flashcards'
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

const word = (
  id: number,
  text: string,
  over: Partial<api.WordListItem> = {}
): api.WordListItem => ({
  id,
  word: text,
  translation: `${text}-en`,
  target_language: 'French',
  native_language: 'English',
  classification: 'not_practiced',
  manual_override: false,
  saved_at: '2026-03-20T10:00:00Z',
  source_conversation_id: null,
  ...over,
})

const words = [
  word(1, 'bonjour', { saved_at: '2026-03-20T10:00:00Z', classification: 'learned' }),
  word(2, 'merci', { saved_at: '2026-03-22T10:00:00Z', classification: 'difficult' }),
  word(3, 'aurevoir', { saved_at: '2026-03-21T10:00:00Z', classification: 'almost_learned' }),
]

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}

const renderPage = () => render(<Flashcards />, { wrapper })

/** Word text in rendered list order, read off each row's delete button. */
const listedWords = () =>
  screen
    .getAllByRole('listitem')
    .map((li) =>
      within(li)
        .getByRole('button', { name: /^Delete / })
        .getAttribute('aria-label')
        ?.replace('Delete ', '')
    )

const enterSelectMode = () =>
  fireEvent.click(screen.getByRole('button', { name: 'Delete multiple' }))

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(api.fetchWords).mockResolvedValue(words)
  vi.mocked(api.deleteWord).mockResolvedValue(undefined)
  vi.mocked(api.deleteWords).mockResolvedValue({ deleted: 2 })
})

describe('Flashcards — loading and empty states', () => {
  it('announces loading while the words are in flight', () => {
    vi.mocked(api.fetchWords).mockReturnValue(new Promise(() => {}))

    renderPage()

    expect(screen.getByText('Loading words…')).toBeInTheDocument()
  })

  it('shows an empty-state hint when there are no words', async () => {
    vi.mocked(api.fetchWords).mockResolvedValue([])

    renderPage()

    expect(await screen.findByText('No words found.')).toBeInTheDocument()
    expect(
      screen.getByText('Save words during a chat conversation to build your vocabulary list.')
    ).toBeInTheDocument()
  })

  it('disables Practice when there is nothing to practise', async () => {
    vi.mocked(api.fetchWords).mockResolvedValue([])

    renderPage()
    await screen.findByText('No words found.')

    expect(screen.getByRole('button', { name: 'Practice' })).toBeDisabled()
  })
})

describe('Flashcards — word list and count', () => {
  it('lists every returned word', async () => {
    renderPage()
    await screen.findByText('bonjour')

    expect(screen.getAllByRole('listitem')).toHaveLength(3)
  })

  it('pluralises the footer count', async () => {
    renderPage()

    expect(await screen.findByText('3 words')).toBeInTheDocument()
  })

  it('uses the singular form for one word', async () => {
    vi.mocked(api.fetchWords).mockResolvedValue([word(1, 'bonjour')])

    renderPage()

    expect(await screen.findByText('1 word')).toBeInTheDocument()
  })
})

describe('Flashcards — sorting', () => {
  it('sorts newest first by default', async () => {
    renderPage()
    await screen.findByText('bonjour')

    expect(listedWords()).toEqual(['merci', 'aurevoir', 'bonjour'])
  })

  it('sorts oldest first', async () => {
    renderPage()
    await screen.findByText('bonjour')

    fireEvent.change(screen.getByRole('combobox', { name: /sort/i }), {
      target: { value: 'saved_at_asc' },
    })

    expect(listedWords()).toEqual(['bonjour', 'aurevoir', 'merci'])
  })

  it('sorts alphabetically', async () => {
    renderPage()
    await screen.findByText('bonjour')

    fireEvent.change(screen.getByRole('combobox', { name: /sort/i }), {
      target: { value: 'word_asc' },
    })

    expect(listedWords()).toEqual(['aurevoir', 'bonjour', 'merci'])
  })

  it('sorts hardest first by classification', async () => {
    renderPage()
    await screen.findByText('bonjour')

    fireEvent.change(screen.getByRole('combobox', { name: /sort/i }), {
      target: { value: 'classification_desc' },
    })

    // difficult > not_practiced > almost_learned > learned
    expect(listedWords()).toEqual(['merci', 'aurevoir', 'bonjour'])
  })
})

describe('Flashcards — filtering', () => {
  it('refetches with the chosen classification', async () => {
    renderPage()
    await screen.findByText('bonjour')

    fireEvent.click(screen.getByRole('button', { name: 'Difficult' }))

    await waitFor(() =>
      expect(api.fetchWords).toHaveBeenCalledWith(
        'es',
        expect.objectContaining({ classification: ['difficult'] })
      )
    )
  })

  it('refetches with a search term', async () => {
    renderPage()
    await screen.findByText('bonjour')

    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'merci' } })

    await waitFor(() =>
      expect(api.fetchWords).toHaveBeenCalledWith('es', expect.objectContaining({ search: 'merci' }))
    )
  })
})

describe('Flashcards — single delete', () => {
  it('deletes a word through the list item', async () => {
    renderPage()
    await screen.findByText('bonjour')

    fireEvent.click(screen.getByRole('button', { name: /delete bonjour/i }))
    fireEvent.click(screen.getByRole('button', { name: /delete\?/i }))

    await waitFor(() => expect(api.deleteWord).toHaveBeenCalledWith(1))
  })

  it('surfaces a delete failure in a banner', async () => {
    vi.mocked(api.deleteWord).mockRejectedValue(new Error('Word is in a deck'))
    renderPage()
    await screen.findByText('bonjour')

    fireEvent.click(screen.getByRole('button', { name: /delete bonjour/i }))
    fireEvent.click(screen.getByRole('button', { name: /delete\?/i }))

    expect(await screen.findByText('Word is in a deck')).toBeInTheDocument()
  })

  it('dismisses the error banner', async () => {
    vi.mocked(api.deleteWord).mockRejectedValue(new Error('Word is in a deck'))
    renderPage()
    await screen.findByText('bonjour')
    fireEvent.click(screen.getByRole('button', { name: /delete bonjour/i }))
    fireEvent.click(screen.getByRole('button', { name: /delete\?/i }))
    await screen.findByText('Word is in a deck')

    fireEvent.click(screen.getByRole('button', { name: /dismiss/i }))

    await waitFor(() => expect(screen.queryByText('Word is in a deck')).not.toBeInTheDocument())
  })
})

describe('Flashcards — bulk selection', () => {
  it('shows no bulk bar until something is selected', async () => {
    renderPage()
    await screen.findByText('bonjour')

    enterSelectMode()

    expect(screen.queryByText(/word.? selected/)).not.toBeInTheDocument()
  })

  it('counts the selected words', async () => {
    renderPage()
    await screen.findByText('bonjour')
    enterSelectMode()

    fireEvent.click(screen.getByRole('checkbox', { name: 'Select bonjour' }))

    expect(await screen.findByText('1 word selected')).toBeInTheDocument()
  })

  it('deselects a word that is clicked twice', async () => {
    renderPage()
    await screen.findByText('bonjour')
    enterSelectMode()
    const box = screen.getByRole('checkbox', { name: 'Select bonjour' })

    fireEvent.click(box)
    await screen.findByText('1 word selected')
    fireEvent.click(box)

    await waitFor(() => expect(screen.queryByText('1 word selected')).not.toBeInTheDocument())
  })

  it('clears the selection when select mode is cancelled', async () => {
    renderPage()
    await screen.findByText('bonjour')
    enterSelectMode()
    fireEvent.click(screen.getByRole('checkbox', { name: 'Select bonjour' }))
    await screen.findByText('1 word selected')

    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))

    await waitFor(() => expect(screen.queryByRole('checkbox')).not.toBeInTheDocument())
  })
})

describe('Flashcards — bulk delete', () => {
  const selectTwoAndConfirm = async () => {
    renderPage()
    await screen.findByText('bonjour')
    enterSelectMode()
    // Select by name, not by index: the rows render in sorted order.
    fireEvent.click(screen.getByRole('checkbox', { name: 'Select bonjour' }))
    fireEvent.click(screen.getByRole('checkbox', { name: 'Select merci' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Delete 2 words' }))
    return screen.findByRole('dialog')
  }

  it('asks for confirmation before deleting', async () => {
    const dialog = await selectTwoAndConfirm()

    expect(within(dialog).getByText('Delete 2 words?')).toBeInTheDocument()
    expect(within(dialog).getByText('This cannot be undone.')).toBeInTheDocument()
    expect(api.deleteWords).not.toHaveBeenCalled()
  })

  it('deletes the selected ids on confirm', async () => {
    const dialog = await selectTwoAndConfirm()

    fireEvent.click(within(dialog).getByRole('button', { name: 'Delete' }))

    await waitFor(() => expect(api.deleteWords).toHaveBeenCalledWith([1, 2]))
  })

  it('leaves select mode after a successful bulk delete', async () => {
    const dialog = await selectTwoAndConfirm()

    fireEvent.click(within(dialog).getByRole('button', { name: 'Delete' }))

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()
  })

  it('closes the dialog on Cancel without deleting', async () => {
    const dialog = await selectTwoAndConfirm()

    fireEvent.click(within(dialog).getByRole('button', { name: 'Cancel' }))

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(api.deleteWords).not.toHaveBeenCalled()
  })

  it('closes the dialog when the backdrop is clicked', async () => {
    const dialog = await selectTwoAndConfirm()

    fireEvent.click(dialog)

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  })

  it('keeps the dialog open when the panel inside it is clicked', async () => {
    const dialog = await selectTwoAndConfirm()

    fireEvent.click(within(dialog).getByText('This cannot be undone.'))

    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })

  it('surfaces a bulk delete failure', async () => {
    vi.mocked(api.deleteWords).mockRejectedValue(new Error('Some words are in decks'))
    const dialog = await selectTwoAndConfirm()

    fireEvent.click(within(dialog).getByRole('button', { name: 'Delete' }))

    expect(await screen.findByText('Some words are in decks')).toBeInTheDocument()
  })
})

describe('Flashcards — navigation', () => {
  it.each([
    ['Back to Home', '/'],
    ['Analytics', '/flashcards/analytics'],
    ['My Decks', '/flashcards/decks'],
    ['Practice', '/flashcards/decks'],
  ])('navigates from %s', async (name, path) => {
    renderPage()
    await screen.findByText('bonjour')

    fireEvent.click(screen.getByRole('button', { name }))

    expect(mockNavigate).toHaveBeenCalledWith(path)
  })
})
