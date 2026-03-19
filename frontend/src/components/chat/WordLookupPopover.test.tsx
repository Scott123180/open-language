import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import WordLookupPopover from './WordLookupPopover'

const baseProps = {
  word: 'hola',
  result: null,
  isLoading: false,
  onSave: vi.fn(),
  onClose: vi.fn(),
}

describe('WordLookupPopover', () => {
  it('renders with selection text as heading/label', () => {
    render(<WordLookupPopover {...baseProps} />)
    expect(screen.getByText('hola')).toBeInTheDocument()
  })

  it('shows translation result text when result prop provided', () => {
    render(<WordLookupPopover {...baseProps} result="hello" />)
    expect(screen.getByText('hello')).toBeInTheDocument()
  })

  it('shows Save Word button', () => {
    render(<WordLookupPopover {...baseProps} result="hello" />)
    expect(screen.getByRole('button', { name: 'Save Word' })).toBeInTheDocument()
  })

  it('clicking Save Word calls onSave callback with the word', () => {
    const onSave = vi.fn()
    render(<WordLookupPopover {...baseProps} result="hello" onSave={onSave} />)
    fireEvent.click(screen.getByRole('button', { name: 'Save Word' }))
    expect(onSave).toHaveBeenCalledWith('hola')
  })

  it('shows loading state when isLoading=true', () => {
    render(<WordLookupPopover {...baseProps} isLoading={true} />)
    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('has proper accessible dialog role', () => {
    render(<WordLookupPopover {...baseProps} />)
    expect(screen.getByRole('dialog', { name: 'Word lookup' })).toBeInTheDocument()
  })

  it('clicking close button calls onClose callback', () => {
    const onClose = vi.fn()
    render(<WordLookupPopover {...baseProps} onClose={onClose} />)
    fireEvent.click(screen.getByRole('button', { name: 'Close' }))
    expect(onClose).toHaveBeenCalledTimes(1)
  })
})
