import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import DeckConfigPanel from './DeckConfigPanel'
import * as api from '../../services/flashcardsApi'

vi.mock('../../services/flashcardsApi')
// The Flashcards screens show the practice language's data; Spanish here.
vi.mock('../../hooks/usePracticeLanguages', () => ({
  usePracticeLanguages: () => ({
    current: { language_id: 'es', display_name: 'Spanish' },
    languages: [],
    nameOf: (id: string) => id,
    isLoading: false,
    error: null,
  }),
}))

const onCreated = vi.fn()
const onCancel = vi.fn()

const createdDeck = { id: 7, name: 'Deck 7' } as api.DeckDetail

const renderPanel = () => render(<DeckConfigPanel onCreated={onCreated} onCancel={onCancel} />)

const next = () => fireEvent.click(screen.getByRole('button', { name: 'Next →' }))
const back = () => fireEvent.click(screen.getByRole('button', { name: 'Back' }))
const generate = () => fireEvent.click(screen.getByRole('button', { name: 'Generate Deck' }))

/** Walks the wizard to the final step, leaving every default in place. */
const goToLastStep = () => {
  next()
  next()
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(api.createDeck).mockResolvedValue(createdDeck)
})

describe('DeckConfigPanel — step 1, size', () => {
  it('opens on the size step', () => {
    renderPanel()

    expect(screen.getByRole('heading', { name: 'How many cards?' })).toBeInTheDocument()
    expect(
      screen.getByText('Choose a session size. You can always create more decks later.')
    ).toBeInTheDocument()
  })

  it('offers the three size presets', () => {
    renderPanel()

    expect(screen.getByText('Quick session')).toBeInTheDocument()
    expect(screen.getByText('Standard')).toBeInTheDocument()
    expect(screen.getByText('Deep dive')).toBeInTheDocument()
  })

  it('reveals a number input when Custom is chosen', () => {
    renderPanel()

    expect(screen.queryByLabelText('Custom deck size')).not.toBeInTheDocument()

    fireEvent.click(screen.getByText('Custom'))

    expect(screen.getByLabelText('Custom deck size')).toBeInTheDocument()
  })

  it('blocks advancing while the custom size is empty', () => {
    renderPanel()
    fireEvent.click(screen.getByText('Custom'))

    expect(screen.getByRole('button', { name: 'Next →' })).toBeDisabled()
  })

  it('blocks advancing on a custom size of zero', () => {
    renderPanel()
    fireEvent.click(screen.getByText('Custom'))

    fireEvent.change(screen.getByLabelText('Custom deck size'), { target: { value: '0' } })

    expect(screen.getByRole('button', { name: 'Next →' })).toBeDisabled()
  })

  it('allows advancing once a valid custom size is typed', () => {
    renderPanel()
    fireEvent.click(screen.getByText('Custom'))

    fireEvent.change(screen.getByLabelText('Custom deck size'), { target: { value: '15' } })

    expect(screen.getByRole('button', { name: 'Next →' })).toBeEnabled()
  })

  it('returns to a preset after a custom size was entered', () => {
    renderPanel()
    fireEvent.click(screen.getByText('Custom'))
    fireEvent.change(screen.getByLabelText('Custom deck size'), { target: { value: '15' } })

    fireEvent.click(screen.getByText('Quick session'))

    expect(screen.queryByLabelText('Custom deck size')).not.toBeInTheDocument()
  })

  it('shows Cancel rather than Back on the first step', () => {
    renderPanel()

    expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Back' })).not.toBeInTheDocument()
  })

  it('cancels out of the wizard', () => {
    renderPanel()

    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(onCancel).toHaveBeenCalledOnce()
  })
})

describe('DeckConfigPanel — step 2, practice mode', () => {
  it('lists every practice mode with its description', () => {
    renderPanel()

    next()

    expect(screen.getByRole('heading', { name: 'How do you want to practice?' })).toBeInTheDocument()
    expect(screen.getByText('See the word, recall its translation')).toBeInTheDocument()
    expect(screen.getByText('Hear the audio only, recall the translation')).toBeInTheDocument()
    expect(screen.getByText('See the translation, produce the word')).toBeInTheDocument()
    expect(screen.getByText('Complete a sentence with the missing word')).toBeInTheDocument()
  })

  it('offers Back from the second step', () => {
    renderPanel()

    next()

    expect(screen.getByRole('button', { name: 'Back' })).toBeInTheDocument()
  })

  it('returns to the size step', () => {
    renderPanel()
    next()

    back()

    expect(screen.getByRole('heading', { name: 'How many cards?' })).toBeInTheDocument()
  })
})

describe('DeckConfigPanel — step 3, algorithm', () => {
  it('lists every algorithm with its description', () => {
    renderPanel()

    goToLastStep()

    expect(screen.getByRole('heading', { name: 'Which words?' })).toBeInTheDocument()
    expect(screen.getByText('A balanced mix of all your words')).toBeInTheDocument()
    expect(screen.getByText('Focus on words you have never practiced')).toBeInTheDocument()
    expect(screen.getByText('Words you consistently struggle with')).toBeInTheDocument()
    expect(screen.getByText('Words you are close to mastering')).toBeInTheDocument()
  })

  it('swaps Next for Generate Deck on the last step', () => {
    renderPanel()

    goToLastStep()

    expect(screen.queryByRole('button', { name: 'Next →' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Generate Deck' })).toBeInTheDocument()
  })
})

describe('DeckConfigPanel — generating', () => {
  it('creates a deck from the defaults', async () => {
    renderPanel()
    goToLastStep()

    generate()

    await waitFor(() =>
      expect(api.createDeck).toHaveBeenCalledWith({
        language: 'es',
        size: 20,
        word_source: 'all',
        practice_mode: 'recall',
        algorithm: 'mixed_review',
      })
    )
  })

  it('creates a deck from the chosen mode and algorithm', async () => {
    renderPanel()
    fireEvent.click(screen.getByText('Deep dive'))
    next()
    fireEvent.click(screen.getByText('Hear the audio only, recall the translation'))
    next()
    fireEvent.click(screen.getByText('Words you consistently struggle with'))

    generate()

    await waitFor(() =>
      expect(api.createDeck).toHaveBeenCalledWith({
        language: 'es',
        size: 40,
        word_source: 'all',
        practice_mode: 'listen',
        algorithm: 'difficult',
      })
    )
  })

  it('creates a deck at the custom size', async () => {
    renderPanel()
    fireEvent.click(screen.getByText('Custom'))
    fireEvent.change(screen.getByLabelText('Custom deck size'), { target: { value: '7' } })
    goToLastStep()

    generate()

    await waitFor(() =>
      expect(api.createDeck).toHaveBeenCalledWith(expect.objectContaining({ size: 7 }))
    )
  })

  it('hands the created deck back to the caller', async () => {
    renderPanel()
    goToLastStep()

    generate()

    await waitFor(() => expect(onCreated).toHaveBeenCalledWith(createdDeck))
  })

  it('shows a pending label while the deck is being built', async () => {
    vi.mocked(api.createDeck).mockReturnValue(new Promise(() => {}))
    renderPanel()
    goToLastStep()

    generate()

    expect(await screen.findByRole('button', { name: 'Generating…' })).toBeDisabled()
  })

  it('surfaces the server message and stays on the step', async () => {
    vi.mocked(api.createDeck).mockRejectedValue(new Error('Not enough words saved'))
    renderPanel()
    goToLastStep()

    generate()

    expect(await screen.findByRole('alert')).toHaveTextContent('Not enough words saved')
    expect(onCreated).not.toHaveBeenCalled()
  })

  it('falls back to a generic message for a non-Error rejection', async () => {
    vi.mocked(api.createDeck).mockRejectedValue('nope')
    renderPanel()
    goToLastStep()

    generate()

    expect(await screen.findByRole('alert')).toHaveTextContent('Failed to create deck')
  })

  it('re-enables the button after a failure so it can be retried', async () => {
    vi.mocked(api.createDeck).mockRejectedValue(new Error('Not enough words saved'))
    renderPanel()
    goToLastStep()
    generate()
    await screen.findByRole('alert')

    expect(screen.getByRole('button', { name: 'Generate Deck' })).toBeEnabled()
  })
})
