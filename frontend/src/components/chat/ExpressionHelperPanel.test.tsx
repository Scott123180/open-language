import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ExpressionHelperPanel from './ExpressionHelperPanel'

vi.mock('../../services/api', () => ({
  streamHelper: vi.fn(),
}))

import * as api from '../../services/api'

const baseProps = {
  conversationId: 7,
  targetName: 'German',
  nativeName: 'English',
  onClose: vi.fn(),
}

/** streamHelper(content, sessionId, conversationId, onToken, onDone, onError) */
const resolveImmediately = () =>
  vi.mocked(api.streamHelper).mockImplementation(
    async (_content, _sessionId, _conversationId, _onToken, onDone, _onError) => {
      onDone()
    }
  )

const send = (text: string) => {
  fireEvent.change(screen.getByRole('textbox'), { target: { value: text } })
  fireEvent.click(screen.getByRole('button', { name: /ask expression helper/i }))
}

describe('ExpressionHelperPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // Visibility is the parent's job: Chat.tsx mounts this panel only while
  // helperExpanded is true, so the panel itself is always open.
  it('renders its input and send button as soon as it is mounted', () => {
    render(<ExpressionHelperPanel {...baseProps} />)
    expect(screen.getByRole('textbox')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /ask expression helper/i })).toBeInTheDocument()
  })

  it('asks the parent to close it when the close button is clicked', () => {
    render(<ExpressionHelperPanel {...baseProps} />)
    fireEvent.click(screen.getByRole('button', { name: /close expression helper/i }))
    expect(baseProps.onClose).toHaveBeenCalledOnce()
  })

  it('starts with its own empty message list', () => {
    render(<ExpressionHelperPanel {...baseProps} />)
    expect(screen.queryAllByRole('article')).toHaveLength(0)
  })

  it('shows a sent message in the helper own message list', async () => {
    resolveImmediately()
    render(<ExpressionHelperPanel {...baseProps} />)

    send('How do I say hello?')

    expect(await screen.findByText('How do I say hello?')).toBeInTheDocument()
  })

  it('keeps helper messages out of the main chat', async () => {
    resolveImmediately()
    const { container } = render(
      <div>
        <div data-testid="main-chat" />
        <ExpressionHelperPanel {...baseProps} />
      </div>
    )

    send('Test message')
    await screen.findByText('Test message')

    expect(container.querySelector('[data-testid="main-chat"]')?.textContent).toBe('')
  })
})

describe('ExpressionHelperPanel — conversation languages (006)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('labels the direction with the conversation languages', () => {
    render(<ExpressionHelperPanel {...baseProps} />)

    expect(screen.getByText('English → German')).toBeInTheDocument()
  })

  it('asks the helper about this conversation', async () => {
    resolveImmediately()
    render(<ExpressionHelperPanel {...baseProps} />)

    send('How do I say hello?')

    await screen.findByText('How do I say hello?')
    expect(vi.mocked(api.streamHelper).mock.calls[0][2]).toBe(7)
  })
})
