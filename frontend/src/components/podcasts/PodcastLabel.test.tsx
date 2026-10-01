import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import PodcastLabel from './PodcastLabel'

describe('PodcastLabel', () => {
  it('reads Podcast, the format and the host', () => {
    render(<PodcastLabel formatLabel="One host" hostNames={['Lucía']} />)

    expect(screen.getByText('Podcast · One host · Lucía')).toBeInTheDocument()
  })

  it('joins two hosts', () => {
    render(<PodcastLabel formatLabel="Panel" hostNames={['Lucía', 'Marco']} />)

    expect(screen.getByText('Podcast · Panel · Lucía & Marco')).toBeInTheDocument()
  })
})
