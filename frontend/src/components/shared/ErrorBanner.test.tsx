import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import ErrorBanner from './ErrorBanner'

describe('ErrorBanner', () => {
  it('renders the error message', () => {
    render(<ErrorBanner message="Something went wrong" />)
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
  })

  it('has role="alert" for accessibility', () => {
    render(<ErrorBanner message="Error!" />)
    expect(screen.getByRole('alert')).toBeInTheDocument()
  })

  it('has aria-live="assertive"', () => {
    render(<ErrorBanner message="Error!" />)
    expect(screen.getByRole('alert')).toHaveAttribute('aria-live', 'assertive')
  })

  it('disappears when dismiss button is clicked', () => {
    render(<ErrorBanner message="Oops" />)
    fireEvent.click(screen.getByRole('button', { name: /dismiss error/i }))
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('calls onDismiss callback when dismissed', () => {
    const onDismiss = vi.fn()
    render(<ErrorBanner message="Oops" onDismiss={onDismiss} />)
    fireEvent.click(screen.getByRole('button', { name: /dismiss error/i }))
    expect(onDismiss).toHaveBeenCalledOnce()
  })

  it('dismiss button has accessible label', () => {
    render(<ErrorBanner message="Error!" />)
    expect(screen.getByRole('button', { name: /dismiss error/i })).toBeInTheDocument()
  })
})
