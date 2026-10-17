import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import ShowCard from './ShowCard'
import { personalities, show } from './fixtures.test.utils'

describe('ShowCard', () => {
  it('is a button named by the show title', () => {
    render(<ShowCard show={show} personalities={personalities} onChoose={vi.fn()} />)

    expect(screen.getByRole('button', { name: 'Weekend Food Talk' })).toBeInTheDocument()
  })

  it('shows the topic above the title', () => {
    render(<ShowCard show={show} personalities={personalities} onChoose={vi.fn()} />)

    const topic = screen.getByText('food')
    const title = screen.getByText('Weekend Food Talk')

    expect(topic.compareDocumentPosition(title) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('shows each host by name with their personality', () => {
    render(<ShowCard show={show} personalities={personalities} onChoose={vi.fn()} />)

    for (const text of ['Lucía', 'Enthusiast', 'Marco', 'Dry sceptic']) {
      expect(screen.getByText(text)).toBeInTheDocument()
    }
  })

  it('shows the learner role', () => {
    render(<ShowCard show={show} personalities={personalities} onChoose={vi.fn()} />)

    expect(screen.getByText("You're the guest")).toBeInTheDocument()
  })

  it('describes the topic, the hosts with their personalities and the role to screen readers', () => {
    render(<ShowCard show={show} personalities={personalities} onChoose={vi.fn()} />)

    expect(screen.getByRole('button', { name: 'Weekend Food Talk' })).toHaveAccessibleDescription(
      "Topic: food. Lucía (Enthusiast) & Marco (Dry sceptic). You're the guest.",
    )
  })

  it('chooses the show', () => {
    const onChoose = vi.fn()
    render(<ShowCard show={show} personalities={personalities} onChoose={onChoose} />)

    fireEvent.click(screen.getByRole('button', { name: 'Weekend Food Talk' }))

    expect(onChoose).toHaveBeenCalledWith(show)
  })
})
