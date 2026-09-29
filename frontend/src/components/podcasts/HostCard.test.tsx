import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import HostCard from './HostCard'
import { personalities, show } from './fixtures.test.utils'

const joker = { personality_id: 'joker', label: 'Joker', description: 'Never misses a joke.' }

const renderCard = (overrides: Partial<Parameters<typeof HostCard>[0]> = {}) => {
  const props = {
    host: show.hosts[0],
    personalities: [...personalities, joker],
    otherPersonalityId: 'dry_sceptic',
    isShuffling: false,
    onShuffle: vi.fn(),
    onPersonalityChange: vi.fn(),
    onPlaySample: vi.fn(),
    ...overrides,
  }
  render(<HostCard {...props} />)
  return props
}

describe('HostCard', () => {
  it('shows the host name', () => {
    renderCard()

    expect(screen.getByText('Lucía')).toBeInTheDocument()
  })

  it('has a labelled personality choice on the hosts personality', () => {
    renderCard()

    expect(screen.getByLabelText("Lucía's personality")).toHaveValue('enthusiast')
  })

  it('offers every personality except the other hosts', () => {
    renderCard()

    const options = screen.getAllByRole('option').map((option) => option.textContent)
    expect(options).toEqual(['Enthusiast', 'Joker'])
  })

  it('offers every personality when there is no other host', () => {
    renderCard({ otherPersonalityId: null })

    expect(screen.getAllByRole('option')).toHaveLength(3)
  })

  it('reports a changed personality', () => {
    const props = renderCard()

    fireEvent.change(screen.getByLabelText("Lucía's personality"), { target: { value: 'joker' } })

    expect(props.onPersonalityChange).toHaveBeenCalledWith('joker')
  })

  it('shuffles the host', () => {
    const props = renderCard()

    fireEvent.click(screen.getByRole('button', { name: 'Shuffle Lucía' }))

    expect(props.onShuffle).toHaveBeenCalled()
  })

  it('cannot shuffle again while a shuffle is on its way', () => {
    renderCard({ isShuffling: true })

    expect(screen.getByRole('button', { name: 'Shuffle Lucía' })).toBeDisabled()
  })

  it('plays a sample of the hosts voice', () => {
    const props = renderCard()

    fireEvent.click(screen.getByRole('button', { name: "Play Lucía's voice" }))

    expect(props.onPlaySample).toHaveBeenCalled()
  })
})
