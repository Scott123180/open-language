import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import MessageBubble from './MessageBubble'

describe('MessageBubble', () => {
  it('renders content text', () => {
    render(<MessageBubble role="user" content="Hello there!" />)
    expect(screen.getByText('Hello there!')).toBeInTheDocument()
  })

  it('applies correct aria-label for user role', () => {
    render(<MessageBubble role="user" content="Hi" />)
    expect(screen.getByRole('article', { name: 'Your message' })).toBeInTheDocument()
  })

  it('applies correct aria-label for assistant role', () => {
    render(<MessageBubble role="assistant" content="Hello!" />)
    expect(screen.getByRole('article', { name: 'AI response' })).toBeInTheDocument()
  })

  it('renders children when provided', () => {
    render(
      <MessageBubble role="assistant" content="Response">
        <button>Translate</button>
      </MessageBubble>,
    )
    expect(screen.getByRole('button', { name: 'Translate' })).toBeInTheDocument()
  })

  it('shows streaming indicator when isStreaming=true', () => {
    render(<MessageBubble role="assistant" content="Typing" isStreaming={true} />)
    // The blinking cursor span is aria-hidden; check it exists via aria-hidden query
    const article = screen.getByRole('article')
    const cursor = article.querySelector('[aria-hidden="true"]')
    expect(cursor).toBeInTheDocument()
  })

  it('does not show streaming indicator when isStreaming=false', () => {
    render(<MessageBubble role="assistant" content="Done" isStreaming={false} />)
    const article = screen.getByRole('article')
    const cursor = article.querySelector('[aria-hidden="true"]')
    expect(cursor).not.toBeInTheDocument()
  })

  it('user bubble is right-aligned and assistant is left-aligned', () => {
    const { rerender } = render(<MessageBubble role="user" content="Hi" />)
    let article = screen.getByRole('article')
    expect(article).toHaveStyle({ alignItems: 'flex-end' })

    rerender(<MessageBubble role="assistant" content="Hi" />)
    article = screen.getByRole('article')
    expect(article).toHaveStyle({ alignItems: 'flex-start' })
  })
})
