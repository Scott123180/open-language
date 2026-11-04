import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import ArrivingLine from './ArrivingLine'
import { lucia } from './fixtures.test.utils'

const arriving = {
  streamId: 's1',
  hostId: lucia.host_id,
  parts: [
    { event: 'line_part' as const, stream_id: 's1', index: 0, text: 'Hola a todos.', audio_url: '/p/0' },
    { event: 'line_part' as const, stream_id: 's1', index: 1, text: 'Hoy hablamos de pan.', audio_url: '/p/1' },
  ],
}

describe('ArrivingLine (011 research R13)', () => {
  it('shows the host and the sentences so far, marked as still arriving', () => {
    render(<ArrivingLine arriving={arriving} host={lucia} isHidden={false} />)

    expect(screen.getByText('Lucía')).toBeInTheDocument()
    expect(screen.getByText('Hola a todos. Hoy hablamos de pan.')).toBeInTheDocument()
    expect(screen.getByTestId('arriving-line')).toHaveAttribute('aria-busy', 'true')
  })

  it('offers no Replay or Slower until the line has arrived', () => {
    render(<ArrivingLine arriving={arriving} host={lucia} isHidden={false} />)

    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('keeps the words hidden in Listen with Show text off', () => {
    render(<ArrivingLine arriving={arriving} host={lucia} isHidden />)

    expect(screen.queryByText(/Hola a todos/)).not.toBeInTheDocument()
    expect(screen.getByText('Lucía is speaking…')).toBeInTheDocument()
  })
})
