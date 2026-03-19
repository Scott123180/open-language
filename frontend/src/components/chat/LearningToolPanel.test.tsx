import { render, screen, fireEvent, waitFor } from '@testing-library/react'
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
  targetLanguage: 'Spanish',
  nativeLanguage: 'English',
}

describe('LearningToolPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders Grammar and Alternative Phrasing buttons for user messages', () => {
    render(<LearningToolPanel {...baseProps} role="user" />)
    expect(screen.getByRole('button', { name: 'Grammar' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Translate' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Alternative Phrasing' })).toBeInTheDocument()
  })

  it('renders only Translate button for assistant messages', () => {
    render(<LearningToolPanel {...baseProps} role="assistant" />)
    expect(screen.getByRole('button', { name: 'Translate' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Grammar' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Alternative Phrasing' })).not.toBeInTheDocument()
  })

  it('clicking Grammar triggers the grammar API call', async () => {
    vi.mocked(api.checkGrammar).mockResolvedValue({ result: 'Looks good!', cached: false })
    render(<LearningToolPanel {...baseProps} role="user" />)
    fireEvent.click(screen.getByRole('button', { name: 'Grammar' }))
    await waitFor(() => expect(api.checkGrammar).toHaveBeenCalledWith(1))
  })

  it('shows loading spinner on a button while that tool is loading', async () => {
    let resolve: (v: { result: string; cached: boolean }) => void
    const pending = new Promise<{ result: string; cached: boolean }>((res) => { resolve = res })
    vi.mocked(api.checkGrammar).mockReturnValue(pending)

    render(<LearningToolPanel {...baseProps} role="user" />)
    fireEvent.click(screen.getByRole('button', { name: 'Grammar' }))

    expect(await screen.findByRole('status')).toBeInTheDocument()
    resolve!({ result: 'Looks good!', cached: false })
  })

  it('shows result text after result is returned', async () => {
    vi.mocked(api.checkGrammar).mockResolvedValue({ result: 'Your grammar is correct.', cached: false })
    render(<LearningToolPanel {...baseProps} role="user" />)
    fireEvent.click(screen.getByRole('button', { name: 'Grammar' }))
    expect(await screen.findByText('Your grammar is correct.')).toBeInTheDocument()
  })

  it('result panel is visible after result returned', async () => {
    vi.mocked(api.checkGrammar).mockResolvedValue({ result: 'Looks good!', cached: false })
    render(<LearningToolPanel {...baseProps} role="user" />)
    fireEvent.click(screen.getByRole('button', { name: 'Grammar' }))
    expect(await screen.findByText('Looks good!')).toBeVisible()
  })

  it('clicking a different button while result shown replaces the result panel', async () => {
    vi.mocked(api.checkGrammar).mockResolvedValue({ result: 'Grammar result', cached: false })
    vi.mocked(api.translateMessage).mockResolvedValue({ result: 'Translation result', cached: false })

    render(<LearningToolPanel {...baseProps} role="user" />)
    fireEvent.click(screen.getByRole('button', { name: 'Grammar' }))
    await screen.findByText('Grammar result')

    fireEvent.click(screen.getByRole('button', { name: 'Translate' }))
    await screen.findByText('Translation result')
    expect(screen.queryByText('Grammar result')).not.toBeInTheDocument()
  })
})
