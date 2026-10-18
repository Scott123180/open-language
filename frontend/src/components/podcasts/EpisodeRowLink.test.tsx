import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect } from 'vitest'
import type { EpisodeSummaryRow } from '../../services/podcastsApi'
import EpisodeRowLink from './EpisodeRowLink'

const row: EpisodeSummaryRow = {
  conversation_id: 7,
  show_title: 'Big Little Questions',
  format: 'panel',
  format_label: 'Panel',
  host_names: ['Hugo', 'Inés'],
  language: 'es',
  language_name: 'Spanish',
  status: 'completed',
}

const renderRow = (shown: EpisodeSummaryRow) => render(<EpisodeRowLink row={shown} />, { wrapper: MemoryRouter })

describe('EpisodeRowLink', () => {
  it('shows a series episode\'s number', () => {
    renderRow({ ...row, episode_number: 4 })

    expect(screen.getByText('Podcast · Panel · Hugo & Inés · Episode 4')).toBeInTheDocument()
  })

  it.each([['a one-off', null], ['a pre-010 episode', undefined]])('shows no number for %s', (_, episodeNumber) => {
    renderRow({ ...row, episode_number: episodeNumber })

    expect(screen.getByText('Podcast · Panel · Hugo & Inés')).toBeInTheDocument()
  })
})
