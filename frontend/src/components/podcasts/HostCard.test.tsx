import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import HostCard from './HostCard'
import { show } from './fixtures.test.utils'

describe('HostCard', () => {
  it('shows the host name and personality', () => {
    render(<HostCard host={show.hosts[0]} personalityLabel="Enthusiast" />)

    expect(screen.getByText('Lucía')).toBeInTheDocument()
    expect(screen.getByText('Enthusiast')).toBeInTheDocument()
  })
})
