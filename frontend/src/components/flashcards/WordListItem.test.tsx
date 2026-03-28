import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import WordListItem from './WordListItem'
import type { WordListItem as WordListItemType } from '../../services/flashcardsApi'

const makeWord = (overrides: Partial<WordListItemType> = {}): WordListItemType => ({
  id: 1,
  word: 'bonjour',
  translation: 'hello',
  target_language: 'fr',
  native_language: 'en',
  classification: 'not_practiced',
  manual_override: false,
  saved_at: '2026-03-20T10:00:00Z',
  source_conversation_id: null,
  ...overrides,
})

describe('WordListItem', () => {
  it('renders the word', () => {
    render(<WordListItem word={makeWord()} onDelete={vi.fn()} />)
    expect(screen.getByText('bonjour')).toBeInTheDocument()
  })

  it('renders the translation', () => {
    render(<WordListItem word={makeWord()} onDelete={vi.fn()} />)
    expect(screen.getByText('hello')).toBeInTheDocument()
  })

  it('renders the classification badge', () => {
    render(<WordListItem word={makeWord({ classification: 'difficult' })} onDelete={vi.fn()} />)
    const badge = screen.getByText(/difficult/i)
    expect(badge.tagName.toLowerCase()).toBe('span')
  })

  it('renders a delete button', () => {
    render(<WordListItem word={makeWord()} onDelete={vi.fn()} />)
    expect(screen.getByRole('button', { name: /delete bonjour/i })).toBeInTheDocument()
  })

  it('shows confirm prompt on first delete click', () => {
    render(<WordListItem word={makeWord()} onDelete={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: /delete bonjour/i }))
    expect(screen.getByRole('button', { name: /delete\?/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
  })

  it('calls onDelete after confirming', () => {
    const onDelete = vi.fn()
    render(<WordListItem word={makeWord()} onDelete={onDelete} />)
    fireEvent.click(screen.getByRole('button', { name: /delete bonjour/i }))
    fireEvent.click(screen.getByRole('button', { name: /delete\?/i }))
    expect(onDelete).toHaveBeenCalledWith(1)
  })

  it('cancels delete and restores trash button', () => {
    const onDelete = vi.fn()
    render(<WordListItem word={makeWord()} onDelete={onDelete} />)
    fireEvent.click(screen.getByRole('button', { name: /delete bonjour/i }))
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }))
    expect(onDelete).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: /delete bonjour/i })).toBeInTheDocument()
  })

  it('does not render a checkbox when onToggleSelect is not provided', () => {
    render(<WordListItem word={makeWord()} onDelete={vi.fn()} />)
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()
  })

  it('renders a checkbox when onToggleSelect is provided', () => {
    render(<WordListItem word={makeWord()} onDelete={vi.fn()} onToggleSelect={vi.fn()} isSelected={false} />)
    expect(screen.getByRole('checkbox')).toBeInTheDocument()
  })

  it('calls onToggleSelect when checkbox is clicked', () => {
    const onToggleSelect = vi.fn()
    render(<WordListItem word={makeWord()} onDelete={vi.fn()} onToggleSelect={onToggleSelect} isSelected={false} />)
    fireEvent.click(screen.getByRole('checkbox'))
    expect(onToggleSelect).toHaveBeenCalledWith(1)
  })

  it('checkbox is checked when isSelected is true', () => {
    render(<WordListItem word={makeWord()} onDelete={vi.fn()} onToggleSelect={vi.fn()} isSelected={true} />)
    expect(screen.getByRole('checkbox')).toBeChecked()
  })
})
