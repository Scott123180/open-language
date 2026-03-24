import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import CardPrompt from './CardPrompt'
import type { DeckCardItem } from '../../services/flashcardsApi'

const makeCard = (overrides: Partial<DeckCardItem> = {}): DeckCardItem => ({
  position: 0,
  vocabulary_item_id: 1,
  word: 'bonjour',
  fill_blank_sentence: null,
  ...overrides,
})

describe('CardPrompt — Recall mode', () => {
  it('shows the target-language word as the prompt', () => {
    render(
      <CardPrompt
        card={makeCard()}
        mode="recall"
        nativeWord={null}
        isFlipped={false}
        onFlip={vi.fn()}
      />,
    )
    expect(screen.getByText('bonjour')).toBeInTheDocument()
  })

  it('does not show the native word before flip', () => {
    render(
      <CardPrompt
        card={makeCard()}
        mode="recall"
        nativeWord="hello"
        isFlipped={false}
        onFlip={vi.fn()}
      />,
    )
    expect(screen.queryByText('hello')).not.toBeInTheDocument()
  })

  it('shows the native word translation after flip', () => {
    render(
      <CardPrompt
        card={makeCard()}
        mode="recall"
        nativeWord="hello"
        isFlipped={true}
        onFlip={vi.fn()}
      />,
    )
    expect(screen.getByText('hello')).toBeInTheDocument()
  })

  it('renders a flip button', () => {
    render(
      <CardPrompt
        card={makeCard()}
        mode="recall"
        nativeWord={null}
        isFlipped={false}
        onFlip={vi.fn()}
      />,
    )
    expect(screen.getByRole('button', { name: /flip/i })).toBeInTheDocument()
  })

  it('calls onFlip when flip button is clicked', async () => {
    const onFlip = vi.fn()
    render(
      <CardPrompt
        card={makeCard()}
        mode="recall"
        nativeWord={null}
        isFlipped={false}
        onFlip={onFlip}
      />,
    )
    screen.getByRole('button', { name: /flip/i }).click()
    expect(onFlip).toHaveBeenCalled()
  })
})

describe('CardPrompt — Produce mode', () => {
  it('shows the native-language word as the prompt', () => {
    render(
      <CardPrompt
        card={makeCard()}
        mode="produce"
        nativeWord="hello"
        isFlipped={false}
        onFlip={vi.fn()}
      />,
    )
    expect(screen.getByText('hello')).toBeInTheDocument()
  })

  it('does not show target word before flip in produce mode', () => {
    render(
      <CardPrompt
        card={makeCard()}
        mode="produce"
        nativeWord="hello"
        isFlipped={false}
        onFlip={vi.fn()}
      />,
    )
    expect(screen.queryByText('bonjour')).not.toBeInTheDocument()
  })

  it('shows the target-language word after flip in produce mode', () => {
    render(
      <CardPrompt
        card={makeCard()}
        mode="produce"
        nativeWord="hello"
        isFlipped={true}
        onFlip={vi.fn()}
      />,
    )
    expect(screen.getByText('bonjour')).toBeInTheDocument()
  })
})

describe('CardPrompt — Listen mode', () => {
  it('does not show the target word as text (audio-only prompt)', () => {
    render(
      <CardPrompt
        card={makeCard()}
        mode="listen"
        nativeWord="hello"
        isFlipped={false}
        onFlip={vi.fn()}
      />,
    )
    expect(screen.queryByText('bonjour')).not.toBeInTheDocument()
  })

  it('shows a listen mode indicator', () => {
    render(
      <CardPrompt
        card={makeCard()}
        mode="listen"
        nativeWord="hello"
        isFlipped={false}
        onFlip={vi.fn()}
      />,
    )
    expect(screen.getByRole('button', { name: /flip/i })).toBeInTheDocument()
  })

  it('shows the native translation after flip', () => {
    render(
      <CardPrompt
        card={makeCard()}
        mode="listen"
        nativeWord="hello"
        isFlipped={true}
        onFlip={vi.fn()}
      />,
    )
    expect(screen.getByText('hello')).toBeInTheDocument()
  })
})

describe('CardPrompt — Fill-in-the-Blank mode', () => {
  const cardWithSentence = makeCard({ fill_blank_sentence: 'Je dis ___ à tout le monde.' })

  it('shows the fill-blank sentence with blank', () => {
    render(
      <CardPrompt
        card={cardWithSentence}
        mode="fill_blank"
        nativeWord="hello"
        isFlipped={false}
        onFlip={vi.fn()}
      />,
    )
    expect(screen.getByText(/Je dis ___ à tout le monde\./)).toBeInTheDocument()
  })

  it('does not show the target word directly before flip', () => {
    render(
      <CardPrompt
        card={cardWithSentence}
        mode="fill_blank"
        nativeWord="hello"
        isFlipped={false}
        onFlip={vi.fn()}
      />,
    )
    expect(screen.queryByText('bonjour')).not.toBeInTheDocument()
  })

  it('shows the complete sentence with the word after flip', () => {
    render(
      <CardPrompt
        card={cardWithSentence}
        mode="fill_blank"
        nativeWord="hello"
        isFlipped={true}
        onFlip={vi.fn()}
      />,
    )
    expect(screen.getByText('bonjour')).toBeInTheDocument()
  })
})
