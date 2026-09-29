import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import HostLine from './HostLine'
import { hostLine, lucia } from './fixtures.test.utils'

vi.mock('../../services/api')

describe('HostLine', () => {
  it('shows the speaker name above the full line', () => {
    render(<HostLine line={hostLine} host={lucia} conversationId={57} />)

    expect(screen.getByText('Lucía')).toBeInTheDocument()
    expect(screen.getByText('¡Bienvenidos a Weekend Food Talk!')).toBeInTheDocument()
  })
})
