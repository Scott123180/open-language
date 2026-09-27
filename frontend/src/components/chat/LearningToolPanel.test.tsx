import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import LearningToolPanel from './LearningToolPanel'

vi.mock('../../services/api', () => ({
  checkGrammar: vi.fn(),
  translateMessage: vi.fn(),
  getAlternativePhrasing: vi.fn(),
}))

import * as api from '../../services/api'

const baseProps = {
  messageId: 1,
  content: 'Hello world',
}

describe('LearningToolPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders Grammar and Alternative Phrasing buttons for user messages', () => {
    render(<LearningToolPanel {...baseProps} role="user" />)
    expect(screen.getByRole('button', { name: 'Grammar check' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Translate' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Alternative phrasing' })).toBeInTheDocument()
  })

  it('renders only Translate button for assistant messages', () => {
    render(<LearningToolPanel {...baseProps} role="assistant" />)
    expect(screen.getByRole('button', { name: 'Translate' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Grammar check' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Alternative phrasing' })).not.toBeInTheDocument()
  })

  it('clicking Grammar triggers the grammar API call', async () => {
    vi.mocked(api.checkGrammar).mockResolvedValue({ result: 'Looks good!', cached: false })
    render(<LearningToolPanel {...baseProps} role="user" />)
    fireEvent.click(screen.getByRole('button', { name: 'Grammar check' }))
    await waitFor(() =>
      expect(api.checkGrammar).toHaveBeenCalledWith(1, 'Hello world', undefined)
    )
  })

  it('shows loading spinner on a button while that tool is loading', async () => {
    let resolve: (v: { result: string; cached: boolean }) => void
    const pending = new Promise<{ result: string; cached: boolean }>((res) => { resolve = res })
    vi.mocked(api.checkGrammar).mockReturnValue(pending)

    render(<LearningToolPanel {...baseProps} role="user" />)
    const grammarButton = screen.getByRole('button', { name: 'Grammar check' })
    fireEvent.click(grammarButton)

    // Scoped to the button: the open result panel renders a spinner of its own.
    await waitFor(() => expect(within(grammarButton).getByRole('status')).toBeInTheDocument())
    resolve!({ result: 'Looks good!', cached: false })
  })

  it('shows result text after result is returned', async () => {
    vi.mocked(api.checkGrammar).mockResolvedValue({ result: 'Your grammar is correct.', cached: false })
    render(<LearningToolPanel {...baseProps} role="user" />)
    fireEvent.click(screen.getByRole('button', { name: 'Grammar check' }))
    expect(await screen.findByText('Your grammar is correct.')).toBeInTheDocument()
  })

  it('result panel is visible after result returned', async () => {
    vi.mocked(api.checkGrammar).mockResolvedValue({ result: 'Looks good!', cached: false })
    render(<LearningToolPanel {...baseProps} role="user" />)
    fireEvent.click(screen.getByRole('button', { name: 'Grammar check' }))
    expect(await screen.findByText('Looks good!')).toBeVisible()
  })

  it('clicking a different button while result shown replaces the result panel', async () => {
    vi.mocked(api.checkGrammar).mockResolvedValue({ result: 'Grammar result', cached: false })
    vi.mocked(api.translateMessage).mockResolvedValue({ result: 'Translation result', cached: false })

    render(<LearningToolPanel {...baseProps} role="user" />)
    fireEvent.click(screen.getByRole('button', { name: 'Grammar check' }))
    await screen.findByText('Grammar result')

    fireEvent.click(screen.getByRole('button', { name: 'Translate' }))
    await screen.findByText('Translation result')
    expect(screen.queryByText('Grammar result')).not.toBeInTheDocument()
  })
})

describe('LearningToolPanel — markdown results', () => {
  const markdown = ['Try these:', '', '- one', '- two', '', '1. first', '2. second'].join('\n')

  it('renders bulleted and numbered results from the model', async () => {
    vi.mocked(api.checkGrammar).mockResolvedValue({ result: markdown, cached: false })
    const { container } = render(<LearningToolPanel {...baseProps} role="user" />)

    fireEvent.click(screen.getByRole('button', { name: 'Grammar check' }))
    await screen.findByText('Try these:')

    expect(container.querySelector('ul')).toBeInTheDocument()
    expect(container.querySelector('ol')).toBeInTheDocument()
    expect(screen.getAllByRole('listitem')).toHaveLength(4)
  })

  it('runs the alternative phrasing tool', async () => {
    vi.mocked(api.getAlternativePhrasing).mockResolvedValue({ result: 'Buenas', cached: false })
    render(<LearningToolPanel {...baseProps} role="user" />)

    fireEvent.click(screen.getByRole('button', { name: 'Alternative phrasing' }))

    await waitFor(() =>
      expect(api.getAlternativePhrasing).toHaveBeenCalledWith(1, 'Hello world')
    )
    expect(await screen.findByText('Buenas')).toBeInTheDocument()
  })
})
