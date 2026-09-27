import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import History from './History'
import * as api from '../services/api'

vi.mock('../services/api')

const mockConversations: api.Conversation[] = [
  {
    id: 1,
    scenario_id: 'buy-train-ticket',
    scenario_title: 'Buy a Train Ticket',
    target_language: 'es',
    native_language: 'en',
    target_language_name: 'Spanish',
    native_language_name: 'English',
    status: 'completed',
    started_at: '2026-03-15T10:00:00Z',
    ended_at: '2026-03-15T10:20:00Z',
    llm_model: 'llama3.1',
    custom_prompt: null,
  },
  {
    id: 2,
    scenario_id: 'order-coffee',
    scenario_title: 'Ordering Coffee',
    target_language: 'es',
    native_language: 'en',
    target_language_name: 'Spanish',
    native_language_name: 'English',
    status: 'active',
    started_at: '2026-03-16T09:00:00Z',
    ended_at: null,
    llm_model: 'llama3.1',
    custom_prompt: null,
  },
]

const mockMessages: api.Message[] = [
  {
    id: 10,
    conversation_id: 1,
    role: 'assistant',
    content: 'Hola, ¿en qué puedo ayudarte?',
    input_source: null,
    created_at: '2026-03-15T10:01:00Z',
    tts_audio_path: null,
  },
  {
    id: 11,
    conversation_id: 1,
    role: 'user',
    content: 'Quiero un billete para Madrid.',
    input_source: 'keyboard',
    created_at: '2026-03-15T10:02:00Z',
    tts_audio_path: null,
  },
]

function renderHistory() {
  return render(
    <MemoryRouter>
      <History />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.resetAllMocks()
})

describe('History page', () => {
  it('shows loading state while fetching', () => {
    vi.mocked(api.getConversations).mockReturnValue(new Promise(() => {}))
    renderHistory()
    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })

  it('renders a list of conversations with scenario title and formatted date', async () => {
    vi.mocked(api.getConversations).mockResolvedValue(mockConversations)
    renderHistory()
    await waitFor(() => expect(screen.getByText('Buy a Train Ticket')).toBeInTheDocument())
    expect(screen.getByText('Ordering Coffee')).toBeInTheDocument()
    // formatted date should appear for both conversations
    expect(screen.getAllByText(/2026/i).length).toBeGreaterThanOrEqual(2)
  })

  it('shows "No past conversations yet" when list is empty', async () => {
    vi.mocked(api.getConversations).mockResolvedValue([])
    renderHistory()
    await waitFor(() => expect(screen.getByText(/no past conversations yet/i)).toBeInTheDocument())
  })

  it('clicking a conversation expands inline messages', async () => {
    vi.mocked(api.getConversations).mockResolvedValue(mockConversations)
    vi.mocked(api.getMessages).mockResolvedValue(mockMessages)
    renderHistory()
    await waitFor(() => screen.getByText('Buy a Train Ticket'))

    fireEvent.click(screen.getByText('Buy a Train Ticket'))

    await waitFor(() =>
      expect(screen.getByText('Hola, ¿en qué puedo ayudarte?')).toBeInTheDocument(),
    )
    expect(screen.getByText('Quiero un billete para Madrid.')).toBeInTheDocument()
    expect(api.getMessages).toHaveBeenCalledWith(1)
  })

  it('clicking an expanded conversation collapses it', async () => {
    vi.mocked(api.getConversations).mockResolvedValue(mockConversations)
    vi.mocked(api.getMessages).mockResolvedValue(mockMessages)
    renderHistory()
    await waitFor(() => screen.getByText('Buy a Train Ticket'))

    // expand
    fireEvent.click(screen.getByText('Buy a Train Ticket'))
    await waitFor(() => screen.getByText('Hola, ¿en qué puedo ayudarte?'))

    // collapse
    fireEvent.click(screen.getByText('Buy a Train Ticket'))
    await waitFor(() =>
      expect(screen.queryByText('Hola, ¿en qué puedo ayudarte?')).not.toBeInTheDocument(),
    )
  })
})

describe('History page — conversation languages (006)', () => {
  const german: api.Conversation = {
    ...mockConversations[1],
    id: 3,
    scenario_title: 'Im Café',
    target_language: 'de',
    target_language_name: 'German',
  }

  it('labels each conversation with its own language', async () => {
    vi.mocked(api.getConversations).mockResolvedValue([mockConversations[0], german])
    renderHistory()

    const spanishRow = await screen.findByRole('button', { name: /Buy a Train Ticket/ })
    const germanRow = screen.getByRole('button', { name: /Im Café/ })
    expect(within(spanishRow).getByText('Spanish')).toBeInTheDocument()
    expect(within(germanRow).getByText('German')).toBeInTheDocument()
  })

  it('includes the language in the row name', async () => {
    vi.mocked(api.getConversations).mockResolvedValue([german])
    renderHistory()

    expect(await screen.findByRole('button', { name: /Im Café.*German/ })).toBeInTheDocument()
  })
})
