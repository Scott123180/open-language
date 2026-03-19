import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import Home from './Home'
import * as api from '../services/api'

vi.mock('../services/api')

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
