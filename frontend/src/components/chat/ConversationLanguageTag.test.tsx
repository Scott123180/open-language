import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import ConversationLanguageTag from './ConversationLanguageTag'

describe('ConversationLanguageTag', () => {
  it('shows the language name as plain text', () => {
    render(<ConversationLanguageTag name="German" />)

    expect(screen.getByText('German')).toBeVisible()
  })

  it('is announced as the conversation language', () => {
    const { container } = render(<ConversationLanguageTag name="German" />)

    expect(container.firstElementChild).toHaveTextContent('Conversation language: German')
  })

  it('offers no control to change it', () => {
    render(<ConversationLanguageTag name="German" />)

    expect(screen.queryByRole('combobox')).toBeNull()
    expect(screen.queryByRole('button')).toBeNull()
    expect(screen.queryByRole('link')).toBeNull()
  })

  it('renders nothing before the conversation has loaded', () => {
    const { container } = render(<ConversationLanguageTag name="" />)

    expect(container).toBeEmptyDOMElement()
  })
})
