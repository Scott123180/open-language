import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import ShowCard from './ShowCard'
import { personalities, seriesListing, show } from './fixtures.test.utils'

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

describe('ShowCard with a series (010)', () => {
  it('says which episode is next', () => {
    render(<ShowCard show={seriesListing} personalities={personalities} onChoose={vi.fn()} />)

    expect(screen.getByRole('button', { name: 'Big Little Questions' })).toHaveAccessibleDescription(/Episode 2 next\./)
    expect(screen.getByText('Episode 2 next')).toBeInTheDocument()
  })

  it('says when an episode is unfinished', () => {
    const unfinished = { ...seriesListing, series: { ...seriesListing.series!, unfinished_episode: { conversation_id: 81, episode_number: 1 } } }
    render(<ShowCard show={unfinished} personalities={personalities} onChoose={vi.fn()} />)

    expect(screen.getByRole('button', { name: 'Big Little Questions' })).toHaveAccessibleDescription(/Episode 1 unfinished\./)
  })

  it('says nothing about episodes without a series', () => {
    render(<ShowCard show={show} personalities={personalities} onChoose={vi.fn()} />)

    expect(screen.getByRole('button', { name: 'Weekend Food Talk' })).not.toHaveAccessibleDescription(/Episode/)
  })
})
