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
})
