import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as api from '../../services/api'
import SummaryPanel from './SummaryPanel'

vi.mock('../../services/api')

const ready: api.ConversationSummary = {
  status: 'ready',
  conversation_id: 57,
  up_to_message_id: 9,
  conversation_language: 'de',
  conversation_language_name: 'German',
  native_language_name: 'English',
  points: [
    { conversation_language: 'Lena mag Märkte.', english: 'Lena likes markets.' },
    { conversation_language: 'Jonas findet Tapas teuer.', english: 'Jonas finds tapas expensive.' },
  ],
}

const settings = (summary_language: api.SummaryLanguage) => ({ summary_language }) as api.AppSettings

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(api.getSettings).mockResolvedValue(settings('conversation'))
  vi.mocked(api.updateSettings).mockResolvedValue(settings('native'))
  vi.mocked(api.getConversationSummary).mockResolvedValue(ready)
})

describe('SummaryPanel', () => {
  it('is a labelled region with the points in the conversations language', async () => {
    render(<SummaryPanel conversationId={57} />)

    expect(screen.getByRole('region', { name: 'Conversation summary' })).toBeInTheDocument()
    expect(await screen.findByText('Lena mag Märkte.')).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: 'German' })).toBeChecked()
  })

  it('switches to English at once and remembers the choice', async () => {
    render(<SummaryPanel conversationId={57} />)
    await screen.findByText('Lena mag Märkte.')

    fireEvent.click(screen.getByRole('radio', { name: 'English' }))

    expect(screen.getByText('Lena likes markets.')).toBeInTheDocument()
    expect(screen.queryByText('Lena mag Märkte.')).not.toBeInTheDocument()
    expect(api.updateSettings).toHaveBeenCalledWith({ summary_language: 'native' })
    expect(api.getConversationSummary).toHaveBeenCalledTimes(1)
  })

  it('opens in English when English was chosen last', async () => {
    vi.mocked(api.getSettings).mockResolvedValue(settings('native'))

    render(<SummaryPanel conversationId={57} />)

    expect(await screen.findByText('Lena likes markets.')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByRole('radio', { name: 'English' })).toBeChecked())
  })

  it('says when it is too early', async () => {
    vi.mocked(api.getConversationSummary).mockResolvedValue({ status: 'too_early', message: "There's nothing to summarise yet." })

    render(<SummaryPanel conversationId={57} />)

    expect(await screen.findByText("There's nothing to summarise yet.")).toBeInTheDocument()
  })

  it('shows a failure with Retry', async () => {
    vi.mocked(api.getConversationSummary)
      .mockRejectedValueOnce(new Error('The AI is not responding.'))
      .mockResolvedValueOnce(ready)
    render(<SummaryPanel conversationId={57} />)

    fireEvent.click(await screen.findByRole('button', { name: 'Retry' }))

    expect(await screen.findByText('Lena mag Märkte.')).toBeInTheDocument()
  })
})
