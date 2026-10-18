import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { StartEpisode } from '../../hooks/podcasts/useStartEpisode'
import StartActions from './StartActions'

const starting = (overrides: Partial<StartEpisode> = {}): StartEpisode => ({
  start: vi.fn(),
  isStarting: false,
  error: null,
  catchUp: { phase: 'idle', detail: null },
  retry: vi.fn(),
  startWithoutUpdate: vi.fn(),
  ...overrides,
})

const renderActions = (state: StartEpisode, onStart = vi.fn()) =>
  render(<StartActions label="Start episode 4" starting={state} onStart={onStart} hostNames={['Hugo', 'Inés']} lastEpisode={3} />)

describe('StartActions', () => {
  it('starts the next episode', () => {
    const onStart = vi.fn()
    renderActions(starting(), onStart)

    fireEvent.click(screen.getByRole('button', { name: 'Start episode 4' }))

    expect(onStart).toHaveBeenCalled()
  })

  it('says the hosts are catching up while Start waits', () => {
    renderActions(starting({ isStarting: true, catchUp: { phase: 'catchingUp', detail: null } }))

    expect(screen.getByRole('button', { name: 'Start episode 4' })).toHaveAttribute('aria-busy', 'true')
    expect(screen.getByRole('status')).toHaveTextContent('Hugo and Inés are catching up on episode 3. This takes a few seconds.')
  })

  it('offers Try again and Start without it when the catch-up fails', () => {
    const state = starting({ catchUp: { phase: 'failed', detail: 'Ollama is not running.' } })
    renderActions(state)

    expect(screen.getByRole('status')).toHaveTextContent("The hosts couldn't catch up on episode 3. Ollama is not running.")
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    fireEvent.click(screen.getByRole('button', { name: 'Start without it' }))
    expect(state.retry).toHaveBeenCalled()
    expect(state.startWithoutUpdate).toHaveBeenCalled()
    expect(screen.queryByRole('button', { name: 'Start episode 4' })).not.toBeInTheDocument()
  })

  it('shows a refused start', () => {
    renderActions(starting({ error: "This show's hosts changed. Open the show again." }))

    expect(screen.getByRole('alert')).toHaveTextContent("This show's hosts changed. Open the show again.")
  })
})
