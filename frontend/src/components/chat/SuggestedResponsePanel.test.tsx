import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import SuggestedResponsePanel from './SuggestedResponsePanel'

vi.mock('../../services/api', () => ({
  getSuggestions: vi.fn(),
}))

import * as api from '../../services/api'

describe('SuggestedResponsePanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('is collapsed by default (suggestions not visible)', () => {
    render(<SuggestedResponsePanel conversationId={1} />)
    // The expand button is visible, but suggestion content is not
    expect(screen.getByRole('button', { name: /suggestions/i })).toBeInTheDocument()
    expect(screen.queryByRole('list')).not.toBeInTheDocument()
  })

  it('click expand button shows suggestion text', async () => {
    vi.mocked(api.getSuggestions).mockResolvedValue({
      suggestions: ['Try saying hello', 'Ask about the weather'],
    })
    render(<SuggestedResponsePanel conversationId={1} />)
    fireEvent.click(screen.getByRole('button', { name: /suggestions/i }))
    expect(await screen.findByText('Try saying hello')).toBeInTheDocument()
    expect(screen.getByText('Ask about the weather')).toBeInTheDocument()
  })

  it('suggestion text is not interactive (no click handler on suggestions)', async () => {
    vi.mocked(api.getSuggestions).mockResolvedValue({
      suggestions: ['Try saying hello'],
    })
    render(<SuggestedResponsePanel conversationId={1} />)
    fireEvent.click(screen.getByRole('button', { name: /suggestions/i }))
    const item = await screen.findByText('Try saying hello')
    expect(item.tagName).not.toBe('BUTTON')
    expect(item.closest('button')).toBeNull()
  })

  it('click on suggestion does not call any API', async () => {
    vi.mocked(api.getSuggestions).mockResolvedValue({
      suggestions: ['Try saying hello'],
    })
    render(<SuggestedResponsePanel conversationId={1} />)
    fireEvent.click(screen.getByRole('button', { name: /suggestions/i }))
    const item = await screen.findByText('Try saying hello')
    fireEvent.click(item)
    // only getSuggestions was called (once, on expand), nothing else
    expect(api.getSuggestions).toHaveBeenCalledTimes(1)
  })

  it('collapse button hides suggestions', async () => {
    vi.mocked(api.getSuggestions).mockResolvedValue({
      suggestions: ['Try saying hello'],
    })
    render(<SuggestedResponsePanel conversationId={1} />)
    fireEvent.click(screen.getByRole('button', { name: /suggestions/i }))
    await screen.findByText('Try saying hello')
    fireEvent.click(screen.getByRole('button', { name: /collapse/i }))
    expect(screen.queryByText('Try saying hello')).not.toBeInTheDocument()
  })

  it('shows loading state when fetching', async () => {
    let resolve: (v: { suggestions: string[] }) => void
    const pending = new Promise<{ suggestions: string[] }>((res) => { resolve = res })
    vi.mocked(api.getSuggestions).mockReturnValue(pending)

    render(<SuggestedResponsePanel conversationId={1} />)
    fireEvent.click(screen.getByRole('button', { name: /suggestions/i }))

    expect(await screen.findByRole('status')).toBeInTheDocument()
    resolve!({ suggestions: [] })
  })

  it('reopening shows the same suggestions while nothing new has been said', async () => {
    vi.mocked(api.getSuggestions).mockResolvedValue({ suggestions: ['Try saying hello'] })
    render(<SuggestedResponsePanel conversationId={1} lastMessageId={5} />)
    fireEvent.click(screen.getByRole('button', { name: /suggestions/i }))
    await screen.findByText('Try saying hello')

    fireEvent.click(screen.getByRole('button', { name: /collapse/i }))
    fireEvent.click(screen.getByRole('button', { name: /suggestions/i }))

    expect(await screen.findByText('Try saying hello')).toBeInTheDocument()
    expect(api.getSuggestions).toHaveBeenCalledTimes(1)
  })

  it('reopening after a new message asks for fresh suggestions', async () => {
    vi.mocked(api.getSuggestions)
      .mockResolvedValueOnce({ suggestions: ['First answer'] })
      .mockResolvedValueOnce({ suggestions: ['Second answer'] })
    const { rerender } = render(<SuggestedResponsePanel conversationId={1} lastMessageId={5} />)
    fireEvent.click(screen.getByRole('button', { name: /suggestions/i }))
    await screen.findByText('First answer')
    fireEvent.click(screen.getByRole('button', { name: /collapse/i }))

    rerender(<SuggestedResponsePanel conversationId={1} lastMessageId={7} />)
    fireEvent.click(screen.getByRole('button', { name: /suggestions/i }))

    expect(await screen.findByText('Second answer')).toBeInTheDocument()
    expect(screen.queryByText('First answer')).not.toBeInTheDocument()
  })

  it('an open panel refreshes itself when a new message arrives', async () => {
    vi.mocked(api.getSuggestions)
      .mockResolvedValueOnce({ suggestions: ['First answer'] })
      .mockResolvedValueOnce({ suggestions: ['Second answer'] })
    const { rerender } = render(<SuggestedResponsePanel conversationId={1} lastMessageId={5} />)
    fireEvent.click(screen.getByRole('button', { name: /suggestions/i }))
    await screen.findByText('First answer')

    rerender(<SuggestedResponsePanel conversationId={1} lastMessageId={7} />)

    expect(await screen.findByText('Second answer')).toBeInTheDocument()
  })

  it('an open panel waits for the reply to finish before refreshing', async () => {
    vi.mocked(api.getSuggestions)
      .mockResolvedValueOnce({ suggestions: ['First answer'] })
      .mockResolvedValueOnce({ suggestions: ['Second answer'] })
    const { rerender } = render(<SuggestedResponsePanel conversationId={1} lastMessageId={5} />)
    fireEvent.click(screen.getByRole('button', { name: /suggestions/i }))
    await screen.findByText('First answer')

    rerender(<SuggestedResponsePanel conversationId={1} lastMessageId={6} isDisabled />)
    expect(api.getSuggestions).toHaveBeenCalledTimes(1)
    rerender(<SuggestedResponsePanel conversationId={1} lastMessageId={7} />)

    expect(await screen.findByText('Second answer')).toBeInTheDocument()
    expect(api.getSuggestions).toHaveBeenCalledTimes(2)
  })

  it("asks a screen's own source when one is given (007 episodes)", async () => {
    const fetchSuggestions = vi.fn().mockResolvedValue({ suggestions: ['¡Me encanta!'] })

    render(<SuggestedResponsePanel conversationId={57} fetchSuggestions={fetchSuggestions} />)
    fireEvent.click(screen.getByRole('button', { name: /suggestions/i }))

    expect(await screen.findByText('¡Me encanta!')).toBeInTheDocument()
    expect(fetchSuggestions).toHaveBeenCalledWith(57)
    expect(api.getSuggestions).not.toHaveBeenCalled()
  })
})
