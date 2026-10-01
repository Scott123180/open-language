import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import TurnBanner from './TurnBanner'

describe('TurnBanner', () => {
  it('announces the learners turn', () => {
    render(<TurnBanner turn="learner" speakerName="Lucía" />)

    expect(screen.getByRole('status')).toHaveTextContent('Your turn')
  })

  it('names the speaking host', () => {
    render(<TurnBanner turn="hosts" speakerName="Lucía" />)

    expect(screen.getByRole('status')).toHaveTextContent('Lucía is speaking')
  })

  it('speaks of the hosts before anyone has spoken', () => {
    render(<TurnBanner turn="hosts" speakerName={null} />)

    expect(screen.getByRole('status')).toHaveTextContent('The hosts are speaking')
  })

  it('announces the end', () => {
    render(<TurnBanner turn="finished" speakerName="Lucía" />)

    expect(screen.getByRole('status')).toHaveTextContent('Episode finished')
  })
})
