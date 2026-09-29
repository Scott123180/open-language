import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import EpisodeControls from './EpisodeControls'

const props = { onContinue: vi.fn(), onEnd: vi.fn(), isPending: false }

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
})
