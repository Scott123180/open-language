import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import HelpOverlay from './HelpOverlay'


describe('HelpOverlay', () => {
  it('renders the overlay when open', () => {
    render(<HelpOverlay mode="recall" isOpen={true} onClose={vi.fn()} />)
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })

  it('does not render when closed', () => {
    render(<HelpOverlay mode="recall" isOpen={false} onClose={vi.fn()} />)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('shows recall mode instructions when open', () => {
    render(<HelpOverlay mode="recall" isOpen={true} onClose={vi.fn()} />)
    expect(screen.getByRole('heading', { name: /recall/i })).toBeInTheDocument()
  })

  it('shows listen mode instructions', () => {
    render(<HelpOverlay mode="listen" isOpen={true} onClose={vi.fn()} />)
    expect(screen.getByRole('heading', { name: /listen/i })).toBeInTheDocument()
  })

  it('shows produce mode instructions', () => {
    render(<HelpOverlay mode="produce" isOpen={true} onClose={vi.fn()} />)
    expect(screen.getByRole('heading', { name: /produce/i })).toBeInTheDocument()
  })

  it('shows fill_blank mode instructions', () => {
    render(<HelpOverlay mode="fill_blank" isOpen={true} onClose={vi.fn()} />)
    expect(screen.getByText(/fill.in.the.blank/i)).toBeInTheDocument()
  })

  it('calls onClose when close button is clicked', () => {
    const onClose = vi.fn()
    render(<HelpOverlay mode="recall" isOpen={true} onClose={onClose} />)
    screen.getByRole('button', { name: /close/i }).click()
    expect(onClose).toHaveBeenCalled()
  })
})
