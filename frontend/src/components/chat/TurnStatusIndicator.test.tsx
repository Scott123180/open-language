import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import TurnStatusIndicator from './TurnStatusIndicator'

describe('TurnStatusIndicator', () => {
  it('announces that the sentence is being checked', () => {
    render(<TurnStatusIndicator status="checking" />)
    expect(screen.getByText(/checking your sentence/i)).toBeInTheDocument()
  })

  it('is a polite live region so it does not interrupt', () => {
    render(<TurnStatusIndicator status="checking" />)
    expect(screen.getByRole('status')).toHaveAttribute('aria-live', 'polite')
  })

  it('renders nothing while idle', () => {
    const { container } = render(<TurnStatusIndicator status="idle" />)
    expect(container).toBeEmptyDOMElement()
  })

  it('renders nothing once the reply is streaming', () => {
    const { container } = render(<TurnStatusIndicator status="replying" />)
    expect(container).toBeEmptyDOMElement()
  })

  it('uses design-system tokens rather than hardcoded colours', () => {
    render(<TurnStatusIndicator status="checking" />)
    const style = screen.getByRole('status').getAttribute('style') ?? ''
    expect(style).toContain('var(--color-text-muted)')
    expect(style).not.toMatch(/#[0-9a-f]{3,8}/i)
  })
})
