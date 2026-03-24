import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import WordFilterBar from './WordFilterBar'
import type { WordFilters } from '../../services/flashcardsApi'

const defaultFilters: WordFilters = {}

describe('WordFilterBar', () => {
  it('renders classification filter buttons', () => {
    render(<WordFilterBar filters={defaultFilters} onChange={vi.fn()} />)
    expect(screen.getByRole('button', { name: 'Not Practiced' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Difficult' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Almost Learned' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Learned' })).toBeInTheDocument()
  })

  it('renders search input', () => {
    render(<WordFilterBar filters={defaultFilters} onChange={vi.fn()} />)
    expect(screen.getByRole('searchbox')).toBeInTheDocument()
  })

  it('calls onChange with classification added when filter toggled on', () => {
    const onChange = vi.fn()
    render(<WordFilterBar filters={defaultFilters} onChange={onChange} />)
    fireEvent.click(screen.getByRole('button', { name: 'Difficult' }))
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ classification: expect.arrayContaining(['difficult']) })
    )
  })

  it('calls onChange with classification removed when filter toggled off', () => {
    const onChange = vi.fn()
    const filters: WordFilters = { classification: ['difficult'] }
    render(<WordFilterBar filters={filters} onChange={onChange} />)
    fireEvent.click(screen.getByRole('button', { name: 'Difficult' }))
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ classification: expect.not.arrayContaining(['difficult']) })
    )
  })

  it('calls onChange with search term when user types', () => {
    const onChange = vi.fn()
    render(<WordFilterBar filters={defaultFilters} onChange={onChange} />)
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'bonjour' } })
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ search: 'bonjour' }))
  })

  it('shows pressed state for active classification filters', () => {
    const filters: WordFilters = { classification: ['learned'] }
    render(<WordFilterBar filters={filters} onChange={vi.fn()} />)
    expect(screen.getByRole('button', { name: 'Learned' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: 'Difficult' })).toHaveAttribute('aria-pressed', 'false')
  })
})
