import { render, screen, fireEvent, waitFor } from '@testing-library/react'
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
    status: 'completed',
    started_at: '2026-03-15T10:00:00Z',
    ended_at: '2026-03-15T10:20:00Z',
    llm_model: 'llama3.1',
  },
  {
    id: 2,
    scenario_id: 'order-coffee',
    scenario_title: 'Ordering Coffee',
    target_language: 'es',
    native_language: 'en',
    status: 'active',
    started_at: '2026-03-16T09:00:00Z',
    ended_at: null,
    llm_model: 'llama3.1',
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
