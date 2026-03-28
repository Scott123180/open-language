import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import WordFilterBar from './WordFilterBar'
import type { WordFilters, WordSort } from '../../services/flashcardsApi'

const defaultProps = {
  filters: {} as WordFilters,
  onChange: vi.fn(),
  sort: 'saved_at_desc' as WordSort,
  onSortChange: vi.fn(),
  isSelecting: false,
  onToggleSelecting: vi.fn(),
  hasWords: true,
}

describe('WordFilterBar', () => {
  it('renders classification filter buttons', () => {
    render(<WordFilterBar {...defaultProps} />)
    expect(screen.getByRole('button', { name: 'Not Practiced' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Difficult' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Almost Learned' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Learned' })).toBeInTheDocument()
  })

  it('renders search input', () => {
    render(<WordFilterBar {...defaultProps} />)
    expect(screen.getByRole('searchbox')).toBeInTheDocument()
  })

  it('calls onChange with classification added when filter toggled on', () => {
    const onChange = vi.fn()
    render(<WordFilterBar {...defaultProps} onChange={onChange} />)
    fireEvent.click(screen.getByRole('button', { name: 'Difficult' }))
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ classification: expect.arrayContaining(['difficult']) })
    )
  })

  it('calls onChange with classification removed when filter toggled off', () => {
    const onChange = vi.fn()
    const filters: WordFilters = { classification: ['difficult'] }
    render(<WordFilterBar {...defaultProps} filters={filters} onChange={onChange} />)
    fireEvent.click(screen.getByRole('button', { name: 'Difficult' }))
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ classification: expect.not.arrayContaining(['difficult']) })
    )
  })

  it('calls onChange with search term when user types', () => {
    const onChange = vi.fn()
    render(<WordFilterBar {...defaultProps} onChange={onChange} />)
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'bonjour' } })
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ search: 'bonjour' }))
  })

  it('shows pressed state for active classification filters', () => {
    render(<WordFilterBar {...defaultProps} filters={{ classification: ['learned'] }} />)
    expect(screen.getByRole('button', { name: 'Learned' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: 'Difficult' })).toHaveAttribute('aria-pressed', 'false')
  })

  it('renders sort dropdown with all options', () => {
    render(<WordFilterBar {...defaultProps} />)
    const sortSelect = screen.getByRole('combobox', { name: /sort/i })
    expect(sortSelect).toBeInTheDocument()
    const options = Array.from(sortSelect.querySelectorAll('option')).map((o) => o.value)
    expect(options).toContain('saved_at_desc')
    expect(options).toContain('saved_at_asc')
    expect(options).toContain('word_asc')
    expect(options).toContain('classification_desc')
  })

  it('calls onSortChange when sort selection changes', () => {
    const onSortChange = vi.fn()
    render(<WordFilterBar {...defaultProps} onSortChange={onSortChange} />)
    fireEvent.change(screen.getByRole('combobox', { name: /sort/i }), { target: { value: 'word_asc' } })
    expect(onSortChange).toHaveBeenCalledWith('word_asc')
  })

  it('renders date preset chips', () => {
    render(<WordFilterBar {...defaultProps} />)
    expect(screen.getByRole('button', { name: /this week/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /this month/i })).toBeInTheDocument()
  })

  it('calls onChange with date_from and date_preset when This week is clicked', () => {
    const onChange = vi.fn()
    render(<WordFilterBar {...defaultProps} onChange={onChange} />)
    fireEvent.click(screen.getByRole('button', { name: /this week/i }))
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ date_from: expect.any(String), date_preset: 'week' })
    )
  })

  it('calls onChange with date_from and date_preset when This month is clicked', () => {
    const onChange = vi.fn()
    render(<WordFilterBar {...defaultProps} onChange={onChange} />)
    fireEvent.click(screen.getByRole('button', { name: /this month/i }))
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ date_from: expect.any(String), date_preset: 'month' })
    )
  })

  it('clears date_from when active date preset chip is clicked again', () => {
    const onChange = vi.fn()
    const filters: WordFilters = { date_from: '2026-01-01T00:00:00.000Z', date_preset: 'week' }
    render(<WordFilterBar {...defaultProps} filters={filters} onChange={onChange} />)
    fireEvent.click(screen.getByRole('button', { name: /this week/i }))
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ date_from: undefined, date_preset: undefined })
    )
  })

  it('shows pressed state for active date preset chip', () => {
    render(<WordFilterBar {...defaultProps} filters={{ date_preset: 'month' }} />)
    expect(screen.getByRole('button', { name: /this month/i })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: /this week/i })).toHaveAttribute('aria-pressed', 'false')
  })

  it('renders Delete multiple button', () => {
    render(<WordFilterBar {...defaultProps} />)
    expect(screen.getByRole('button', { name: /delete multiple/i })).toBeInTheDocument()
  })

  it('shows Cancel when isSelecting is true', () => {
    render(<WordFilterBar {...defaultProps} isSelecting={true} />)
    expect(screen.getByRole('button', { name: /cancel/i, hidden: false })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /delete multiple/i })).not.toBeInTheDocument()
  })

  it('calls onToggleSelecting when Delete multiple is clicked', () => {
    const onToggleSelecting = vi.fn()
    render(<WordFilterBar {...defaultProps} onToggleSelecting={onToggleSelecting} />)
    fireEvent.click(screen.getByRole('button', { name: /delete multiple/i }))
    expect(onToggleSelecting).toHaveBeenCalled()
  })

  it('Delete multiple is disabled when hasWords is false', () => {
    render(<WordFilterBar {...defaultProps} hasWords={false} />)
    expect(screen.getByRole('button', { name: /delete multiple/i })).toBeDisabled()
  })
})
