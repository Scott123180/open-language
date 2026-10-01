import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as api from '../../services/api'
import SummaryButton from './SummaryButton'

vi.mock('../../services/api')

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(api.getSettings).mockResolvedValue({ summary_language: 'conversation' } as api.AppSettings)
  vi.mocked(api.getConversationSummary).mockResolvedValue({ status: 'too_early', message: 'Nothing yet.' })
})

describe('SummaryButton', () => {
  it('is a secondary button that toggles the summary panel', async () => {
    render(<SummaryButton conversationId={57} />)
    const button = screen.getByRole('button', { name: 'Summary' })
    expect(button).toHaveAttribute('aria-expanded', 'false')

    fireEvent.click(button)

    expect(button).toHaveAttribute('aria-expanded', 'true')
    expect(await screen.findByRole('region', { name: 'Conversation summary' })).toBeInTheDocument()

    fireEvent.click(button)

    expect(screen.queryByRole('region', { name: 'Conversation summary' })).not.toBeInTheDocument()
  })
})
