import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import ContinueEpisode from './ContinueEpisode'

describe('ContinueEpisode', () => {
  it('offers to continue the unfinished episode first, and a new one after', () => {
    const onContinue = vi.fn()
    const onStartNew = vi.fn()
    render(<ContinueEpisode unfinished={{ conversation_id: 81, episode_number: 1 }} onContinue={onContinue} onStartNew={onStartNew} isStarting={false} />)

    const buttons = screen.getAllByRole('button').map((button) => button.textContent)
    expect(buttons).toEqual(['Continue episode 1', 'Start a new episode instead'])
    fireEvent.click(screen.getByRole('button', { name: 'Continue episode 1' }))
    expect(onContinue).toHaveBeenCalledWith(81)
    fireEvent.click(screen.getByRole('button', { name: 'Start a new episode instead' }))
    expect(onStartNew).toHaveBeenCalled()
  })
})
