import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import Home from './Home'
import * as api from '../services/api'

vi.mock('../services/api')

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => ({
  ...(await vi.importActual<typeof import('react-router-dom')>('react-router-dom')),
  useNavigate: () => mockNavigate,
}))

const mockScenario: api.Scenario = {
  id: 'sc1',
  title: 'Ordering Coffee',
  description: 'Practice ordering a coffee at a café.',
}

function renderHome() {
  return render(
    <MemoryRouter>
      <Home />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.resetAllMocks()
})

describe('Home page', () => {
  it('renders loading state when scenario is loading', async () => {
    vi.mocked(api.getCurrentScenario).mockReturnValue(new Promise(() => {}))
    renderHome()
    expect(screen.getByText(/loading scenario/i)).toBeInTheDocument()
  })

  it('renders scenario card with "Start Chat" button when scenario is loaded', async () => {
    vi.mocked(api.getCurrentScenario).mockResolvedValue(mockScenario)
    renderHome()
    await waitFor(() => expect(screen.getByText('Ordering Coffee')).toBeInTheDocument())
    expect(screen.getByRole('button', { name: /start chat/i })).toBeInTheDocument()
  })

  it('renders a Refresh button', async () => {
    vi.mocked(api.getCurrentScenario).mockResolvedValue(mockScenario)
    renderHome()
    await waitFor(() => screen.getByText('Ordering Coffee'))
    expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument()
  })

  it('clicking Refresh calls api.getNextScenario()', async () => {
    const nextScenario: api.Scenario = { id: 'sc2', title: 'At the Airport', description: 'Navigate the airport.' }
    vi.mocked(api.getCurrentScenario).mockResolvedValue(mockScenario)
    vi.mocked(api.getNextScenario).mockResolvedValue(nextScenario)
    renderHome()
    await waitFor(() => screen.getByRole('button', { name: /refresh/i }))
    fireEvent.click(screen.getByRole('button', { name: /refresh/i }))
    await waitFor(() => expect(api.getNextScenario).toHaveBeenCalledWith(mockScenario.id))
    await waitFor(() => expect(screen.getByText('At the Airport')).toBeInTheDocument())
  })

  it('renders error state when fetch fails', async () => {
    vi.mocked(api.getCurrentScenario).mockRejectedValue(new Error('Network error'))
    renderHome()
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
    expect(screen.getByText(/network error/i)).toBeInTheDocument()
  })
})

describe('Home page — starting a chat', () => {
  beforeEach(() => {
    vi.mocked(api.getCurrentScenario).mockResolvedValue(mockScenario)
  })

  it('creates a conversation from the scenario and opens it', async () => {
    vi.mocked(api.createConversation).mockResolvedValue({ id: 12 } as api.Conversation)
    renderHome()
    await screen.findByText('Ordering Coffee')

    fireEvent.click(screen.getByRole('button', { name: /start chat/i }))

    await waitFor(() => expect(api.createConversation).toHaveBeenCalledWith('sc1'))
    expect(mockNavigate).toHaveBeenCalledWith('/chat/12')
  })

  it('surfaces a failure to start and lets it be dismissed', async () => {
    vi.mocked(api.createConversation).mockRejectedValue(new Error('Ollama down'))
    renderHome()
    await screen.findByText('Ordering Coffee')

    fireEvent.click(screen.getByRole('button', { name: /start chat/i }))
    expect(await screen.findByText('Ollama down')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /dismiss/i }))
    await waitFor(() => expect(screen.queryByText('Ollama down')).not.toBeInTheDocument())
  })

  it('reports a refresh failure', async () => {
    vi.mocked(api.getNextScenario).mockRejectedValue(new Error('No more scenarios'))
    renderHome()
    await screen.findByText('Ordering Coffee')

    fireEvent.click(screen.getByRole('button', { name: /refresh/i }))

    expect(await screen.findByText('No more scenarios')).toBeInTheDocument()
  })
})

describe('Home page — custom scenario', () => {
  beforeEach(() => {
    vi.mocked(api.getCurrentScenario).mockResolvedValue(mockScenario)
  })

  const expandCustom = async () => {
    renderHome()
    await screen.findByText('Ordering Coffee')
    fireEvent.click(screen.getByRole('button', { name: /write your own scenario/i }))
  }

  it('expands and collapses the custom prompt panel', async () => {
    await expandCustom()
    expect(screen.getByLabelText(/describe the situation/i)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /write your own scenario/i }))

    expect(screen.queryByLabelText(/describe the situation/i)).not.toBeInTheDocument()
  })

  it('starts a custom conversation from the typed prompt', async () => {
    vi.mocked(api.createConversation).mockResolvedValue({ id: 15 } as api.Conversation)
    await expandCustom()

    fireEvent.change(screen.getByLabelText(/describe the situation/i), {
      target: { value: '  You are a hotel receptionist.  ' },
    })
    fireEvent.click(screen.getAllByRole('button', { name: /start chat/i })[1])

    await waitFor(() =>
      expect(api.createConversation).toHaveBeenCalledWith(null, 'You are a hotel receptionist.')
    )
    expect(mockNavigate).toHaveBeenCalledWith('/chat/15')
  })

  it('does nothing when the custom prompt is only whitespace', async () => {
    await expandCustom()

    fireEvent.change(screen.getByLabelText(/describe the situation/i), {
      target: { value: '   ' },
    })
    fireEvent.click(screen.getAllByRole('button', { name: /start chat/i })[1])

    await waitFor(() => expect(api.createConversation).not.toHaveBeenCalled())
  })

  it('surfaces a failure to start a custom conversation', async () => {
    vi.mocked(api.createConversation).mockRejectedValue(new Error('Prompt rejected'))
    await expandCustom()

    fireEvent.change(screen.getByLabelText(/describe the situation/i), {
      target: { value: 'Be a barista' },
    })
    fireEvent.click(screen.getAllByRole('button', { name: /start chat/i })[1])

    expect(await screen.findByText('Prompt rejected')).toBeInTheDocument()
  })
})

describe('Home page — theme toggle', () => {
  it('switches between light and dark', async () => {
    vi.mocked(api.getCurrentScenario).mockResolvedValue(mockScenario)
    renderHome()
    await screen.findByText('Ordering Coffee')

    const toggle = screen.getByRole('button', { name: /switch to (light|dark) mode/i })
    const before = toggle.getAttribute('aria-label')

    fireEvent.click(toggle)

    await waitFor(() =>
      expect(
        screen.getByRole('button', { name: /switch to (light|dark) mode/i })
      ).not.toHaveAttribute('aria-label', before)
    )
  })
})

describe('Home page — podcasts (007)', () => {
  it('links to Podcasts from the navigation', async () => {
    vi.mocked(api.getCurrentScenario).mockResolvedValue(mockScenario)

    renderHome()

    expect(await screen.findByRole('link', { name: 'Podcasts' })).toHaveAttribute('href', '/podcasts')
  })
})
