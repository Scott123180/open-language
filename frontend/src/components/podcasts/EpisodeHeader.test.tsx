import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import EpisodeHeader from './EpisodeHeader'
import { episode } from '../../pages/podcastPageFixtures.test.utils'

vi.mock('../chat/ConversationLevelControl', () => ({ default: () => null }))

const renderHeader = (overrides = {}) =>
  render(
    <MemoryRouter>
      <EpisodeHeader episode={episode(overrides)} />
    </MemoryRouter>,
  )

describe('EpisodeHeader', () => {
  it('names the episode of a series', () => {
    renderHeader({ show: { ...episode().show, title: 'Big Little Questions' }, series: { series_id: 4, episode_number: 2 } })

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Big Little Questions · Episode 2')
  })

  it('names the show alone for an episode from before series', () => {
    renderHeader()

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/^Weekend Food Talk$/)
  })
})

describe('EpisodeHeader — a one-off (010 US2)', () => {
  it('names a one-off episode', () => {
    renderHeader({ series: null })

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Weekend Food Talk · One-off')
  })
})

describe('EpisodeHeader — a guest episode (011 US4)', () => {
  const [lucia] = episode().hosts
  const marco = { ...lucia, host_id: 12, slot: 'second' as const, name: 'Marco', show_role: 'co_host' }

  it('names the guest and the host who is away, in words', () => {
    renderHeader({ hosts: [lucia, { ...marco, name: 'Sofía', is_guest: true }], away_host_name: 'Marco' })

    expect(screen.getByText('Guest: Sofía')).toBeInTheDocument()
    expect(screen.getByText('Marco is away')).toBeInTheDocument()
  })

  it('names a guest who replaces nobody without an away line', () => {
    renderHeader({ hosts: [lucia, { ...marco, is_guest: true }], away_host_name: null })

    expect(screen.getByText('Guest: Marco')).toBeInTheDocument()
    expect(screen.queryByText(/is away/)).not.toBeInTheDocument()
  })

  it('says nothing of guests in an episode without one', () => {
    renderHeader()

    expect(screen.queryByText(/^Guest:/)).not.toBeInTheDocument()
  })
})
