import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import ShowCard from './ShowCard'
import { personalities, show } from './fixtures.test.utils'

describe('ShowCard', () => {
  it('is a button named by the show title', () => {
    render(<ShowCard show={show} personalities={personalities} onChoose={vi.fn()} />)

    expect(screen.getByRole('button', { name: 'Weekend Food Talk' })).toBeInTheDocument()
  })

  it('gives the topic, the hosts with their personalities and the learner role', () => {
    render(<ShowCard show={show} personalities={personalities} onChoose={vi.fn()} />)

    expect(screen.getByText(/food/)).toBeInTheDocument()
    expect(screen.getByText('Lucía (Enthusiast) & Marco (Dry sceptic)')).toBeInTheDocument()
    expect(screen.getByText("You're the guest")).toBeInTheDocument()
  })

  it('chooses the show', () => {
    const onChoose = vi.fn()
    render(<ShowCard show={show} personalities={personalities} onChoose={onChoose} />)

    fireEvent.click(screen.getByRole('button', { name: 'Weekend Food Talk' }))

    expect(onChoose).toHaveBeenCalledWith(show)
  })
})
