import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import MessageBubble from './MessageBubble'
import * as api from '../../services/api'

vi.mock('../../services/api')

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

describe('MessageBubble — attached feedback slot', () => {
  it('renders children beneath the message text', () => {
    render(
      <MessageBubble role="user" content="Yo tener veinte años">
        <p>Yo tengo veinte años</p>
      </MessageBubble>,
    )
    const article = screen.getByRole('article')
    const text = screen.getByText('Yo tener veinte años')
    const attached = screen.getByText('Yo tengo veinte años')
    expect(article).toContainElement(attached)
    expect(
      text.compareDocumentPosition(attached) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
  })

  it('renders several attached notes in order', () => {
    render(
      <MessageBubble role="user" content="Yo tener veinte años">
        <p>first note</p>
        <p>second note</p>
      </MessageBubble>,
    )
    expect(screen.getByText('first note')).toBeInTheDocument()
    expect(screen.getByText('second note')).toBeInTheDocument()
  })

  it('renders nothing extra when no children are supplied', () => {
    const { container: withoutChildren } = render(
      <MessageBubble role="user" content="Yo tengo veinte años" />,
    )
    expect(withoutChildren.querySelectorAll('article > div')).toHaveLength(1)
  })
})

describe('MessageBubble — word lookup on selection', () => {
  const lookupProps = {
    role: 'assistant' as const,
    content: 'Hola, ¿qué tal?',
    messageId: 3,
    conversationId: 7,
  }

  /** Makes window.getSelection report `text` over a real range-like rect. */
  const stubSelection = (text: string) =>
    vi.spyOn(window, 'getSelection').mockReturnValue({
      toString: () => text,
      getRangeAt: () => ({
        getBoundingClientRect: () => ({ left: 10, width: 40, bottom: 20 }),
      }),
      removeAllRanges: () => {},
    } as unknown as Selection)

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('looks up a single selected word', async () => {
    stubSelection('Hola')
    vi.mocked(api.lookupWord).mockResolvedValue({ result: 'a greeting', cached: false })
    render(<MessageBubble {...lookupProps} />)

    fireEvent.mouseUp(screen.getByText(lookupProps.content))

    await waitFor(() =>
      expect(api.lookupWord).toHaveBeenCalledWith(3, 'Hola', 'Hola, ¿qué tal?')
    )
    expect(await screen.findByText('a greeting')).toBeInTheDocument()
  })

  it('translates a multi-word selection instead of looking it up', async () => {
    stubSelection('qué tal')
    vi.mocked(api.translateMessage).mockResolvedValue({ result: 'how are you', cached: false })
    render(<MessageBubble {...lookupProps} />)

    fireEvent.mouseUp(screen.getByText(lookupProps.content))

    await waitFor(() =>
      expect(api.translateMessage).toHaveBeenCalledWith(3, 'qué tal')
    )
    expect(api.lookupWord).not.toHaveBeenCalled()
  })

  it('ignores an empty selection', async () => {
    stubSelection('   ')
    render(<MessageBubble {...lookupProps} />)

    fireEvent.mouseUp(screen.getByText(lookupProps.content))

    await waitFor(() => expect(api.lookupWord).not.toHaveBeenCalled())
  })

  it('ignores a selection when the message has no id', async () => {
    stubSelection('Hola')
    render(<MessageBubble role="assistant" content="Hola" />)

    fireEvent.mouseUp(screen.getByText('Hola'))

    await waitFor(() => expect(api.lookupWord).not.toHaveBeenCalled())
  })

  it('shows a definition error when the lookup fails', async () => {
    stubSelection('Hola')
    vi.mocked(api.lookupWord).mockRejectedValue(new Error('offline'))
    render(<MessageBubble {...lookupProps} />)

    fireEvent.mouseUp(screen.getByText(lookupProps.content))

    expect(await screen.findByText('Error loading definition.')).toBeInTheDocument()
  })

  it('shows a translation error when a phrase lookup fails', async () => {
    stubSelection('qué tal')
    vi.mocked(api.translateMessage).mockRejectedValue(new Error('offline'))
    render(<MessageBubble {...lookupProps} />)

    fireEvent.mouseUp(screen.getByText(lookupProps.content))

    expect(await screen.findByText('Error loading translation.')).toBeInTheDocument()
  })

  it('saves the looked-up word and closes the popover', async () => {
    stubSelection('Hola')
    vi.mocked(api.lookupWord).mockResolvedValue({ result: 'a greeting', cached: false })
    vi.mocked(api.saveVocabularyItem).mockResolvedValue({ id: 1 } as never)
    render(<MessageBubble {...lookupProps} />)
    fireEvent.mouseUp(screen.getByText(lookupProps.content))
    await screen.findByText('a greeting')

    fireEvent.click(screen.getByRole('button', { name: /save word/i }))

    await waitFor(() =>
      expect(api.saveVocabularyItem).toHaveBeenCalledWith('Hola', 'a greeting', 7)
    )
    await waitFor(() => expect(screen.queryByText('a greeting')).not.toBeInTheDocument())
  })

  it('closes the popover without saving', async () => {
    stubSelection('Hola')
    vi.mocked(api.lookupWord).mockResolvedValue({ result: 'a greeting', cached: false })
    render(<MessageBubble {...lookupProps} />)
    fireEvent.mouseUp(screen.getByText(lookupProps.content))
    await screen.findByText('a greeting')

    fireEvent.click(screen.getByRole('button', { name: /close/i }))

    await waitFor(() => expect(screen.queryByText('a greeting')).not.toBeInTheDocument())
    expect(api.saveVocabularyItem).not.toHaveBeenCalled()
  })
})
