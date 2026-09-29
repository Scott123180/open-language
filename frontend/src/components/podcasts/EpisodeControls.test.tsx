import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import EpisodeControls from './EpisodeControls'

const props = { onContinue: vi.fn(), onEnd: vi.fn(), onJumpIn: vi.fn(), onPass: vi.fn(), isPending: false, canJumpIn: false, canPass: false }

describe('EpisodeControls', () => {
  it('offers Continue at the hosts continue', () => {
    render(<EpisodeControls {...props} turn="hosts" awaiting="continue" />)

    fireEvent.click(screen.getByRole('button', { name: 'Continue' }))

    expect(props.onContinue).toHaveBeenCalled()
  })

  it('has no Continue at the learners turn', () => {
    render(<EpisodeControls {...props} turn="learner" awaiting={null} />)

    expect(screen.queryByRole('button', { name: 'Continue' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'End episode' })).toBeInTheDocument()
  })

  it('disables both while a line is on its way', () => {
    render(<EpisodeControls {...props} turn="hosts" awaiting="continue" isPending />)

    expect(screen.getByRole('button', { name: 'Continue' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'End episode' })).toBeDisabled()
  })

  it('ends the episode', () => {
    const onEnd = vi.fn()
    render(<EpisodeControls {...props} onEnd={onEnd} turn="learner" awaiting={null} />)

    fireEvent.click(screen.getByRole('button', { name: 'End episode' }))

    expect(onEnd).toHaveBeenCalled()
  })

  it('shows nothing once the episode has finished', () => {
    const { container } = render(<EpisodeControls {...props} turn="finished" awaiting={null} />)

    expect(container).toBeEmptyDOMElement()
  })

  describe('Panel (FR-017)', () => {
    it('offers Jump in while the hosts talk', () => {
      const onJumpIn = vi.fn()
      render(<EpisodeControls {...props} onJumpIn={onJumpIn} canJumpIn turn="hosts" awaiting="continue" />)

      fireEvent.click(screen.getByRole('button', { name: 'Jump in' }))

      expect(onJumpIn).toHaveBeenCalled()
      expect(screen.queryByRole('button', { name: 'Pass' })).not.toBeInTheDocument()
    })

    it('offers Pass at the learners turn', () => {
      const onPass = vi.fn()
      render(<EpisodeControls {...props} onPass={onPass} canPass turn="learner" awaiting={null} />)

      fireEvent.click(screen.getByRole('button', { name: 'Pass' }))

      expect(onPass).toHaveBeenCalled()
      expect(screen.queryByRole('button', { name: 'Jump in' })).not.toBeInTheDocument()
    })

    it('offers neither in One host or Listen', () => {
      render(<EpisodeControls {...props} turn="hosts" awaiting="continue" />)

      expect(screen.queryByRole('button', { name: 'Jump in' })).not.toBeInTheDocument()
      expect(screen.queryByRole('button', { name: 'Pass' })).not.toBeInTheDocument()
    })
  })
})
