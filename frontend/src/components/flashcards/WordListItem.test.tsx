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
    render(<WordListItem word={makeWord()} onDelete={vi.fn()} onClassify={vi.fn()} />)
    expect(screen.getByText('bonjour')).toBeInTheDocument()
  })

  it('renders the translation', () => {
    render(<WordListItem word={makeWord()} onDelete={vi.fn()} onClassify={vi.fn()} />)
    expect(screen.getByText('hello')).toBeInTheDocument()
  })

  it('renders the classification badge', () => {
    render(<WordListItem word={makeWord({ classification: 'difficult' })} onDelete={vi.fn()} onClassify={vi.fn()} />)
    // Badge span and dropdown option both show "Difficult" — use getAllByText
    const matches = screen.getAllByText(/difficult/i)
    expect(matches.length).toBeGreaterThanOrEqual(1)
    expect(matches.some((el) => el.tagName.toLowerCase() === 'span')).toBe(true)
  })

  it('renders a delete button', () => {
    render(<WordListItem word={makeWord()} onDelete={vi.fn()} onClassify={vi.fn()} />)
    expect(screen.getByRole('button', { name: /delete/i })).toBeInTheDocument()
  })

  it('calls onDelete when delete button is clicked', () => {
    const onDelete = vi.fn()
    render(<WordListItem word={makeWord()} onDelete={onDelete} onClassify={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: /delete/i }))
    expect(onDelete).toHaveBeenCalledWith(1)
  })

  it('calls onClassify when classification is changed', () => {
    const onClassify = vi.fn()
    render(<WordListItem word={makeWord()} onDelete={vi.fn()} onClassify={onClassify} />)
    const select = screen.getByRole('combobox', { name: /change classification/i })
    fireEvent.change(select, { target: { value: 'difficult' } })
    expect(onClassify).toHaveBeenCalledWith(1, 'difficult')
  })

  it('shows all classification options in the classify dropdown', () => {
    render(<WordListItem word={makeWord()} onDelete={vi.fn()} onClassify={vi.fn()} />)
    const select = screen.getByRole('combobox', { name: /change classification/i })
    const options = Array.from(select.querySelectorAll('option')).map((o) => o.value)
    expect(options).toContain('not_practiced')
    expect(options).toContain('difficult')
    expect(options).toContain('almost_learned')
    expect(options).toContain('learned')
  })
})
