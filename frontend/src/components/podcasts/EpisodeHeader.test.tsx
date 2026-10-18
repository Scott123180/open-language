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
