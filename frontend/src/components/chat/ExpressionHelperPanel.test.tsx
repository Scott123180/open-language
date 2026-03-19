import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ExpressionHelperPanel from './ExpressionHelperPanel'

vi.mock('../../services/api', () => ({
  streamHelper: vi.fn(),
}))

import * as api from '../../services/api'

const baseProps = {
  targetLanguage: 'Spanish',
  nativeLanguage: 'English',
}

describe('ExpressionHelperPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders collapsed by default', () => {
    render(<ExpressionHelperPanel {...baseProps} />)
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /expression helper/i })).toBeInTheDocument()
  })

  it('expand shows a text input and send button', () => {
    render(<ExpressionHelperPanel {...baseProps} />)
    fireEvent.click(screen.getByRole('button', { name: /expression helper/i }))
    expect(screen.getByRole('textbox')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /send/i })).toBeInTheDocument()
  })

  it('its own message list is separate from main conversation (no shared state)', () => {
    render(<ExpressionHelperPanel {...baseProps} />)
    fireEvent.click(screen.getByRole('button', { name: /expression helper/i }))
    // Helper has its own empty message list — no messages from outside
    const messages = screen.queryAllByRole('article')
    expect(messages).toHaveLength(0)
  })

  it('sending a message shows it in the helpers own message list', async () => {
    vi.mocked(api.streamHelper).mockImplementation(
      async (_content, _sessionId, _onToken, onDone, _onError) => {
        onDone()
      },
    )

    render(<ExpressionHelperPanel {...baseProps} />)
    fireEvent.click(screen.getByRole('button', { name: /expression helper/i }))

    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value: 'How do I say hello?' } })
    fireEvent.click(screen.getByRole('button', { name: /send/i }))

    expect(await screen.findByText('How do I say hello?')).toBeInTheDocument()
  })

  it('helper messages do not appear in the main chat (isolated state)', async () => {
    vi.mocked(api.streamHelper).mockImplementation(
      async (_content, _sessionId, _onToken, onDone, _onError) => {
        onDone()
      },
    )

    const { container } = render(
      <div>
        <div data-testid="main-chat" />
        <ExpressionHelperPanel {...baseProps} />
      </div>,
    )

    fireEvent.click(screen.getByRole('button', { name: /expression helper/i }))
    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value: 'Test message' } })
    fireEvent.click(screen.getByRole('button', { name: /send/i }))

    await screen.findByText('Test message')

    const mainChat = container.querySelector('[data-testid="main-chat"]')
    expect(mainChat?.textContent).toBe('')
  })
})
