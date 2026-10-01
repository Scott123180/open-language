import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import LengthFieldset from './LengthFieldset'
import type { EpisodeLengthOption } from '../../services/podcastsApi'

const lengths: EpisodeLengthOption[] = [
  { length_id: 'short', label: 'Short', target_host_lines: 10, is_default: false },
  { length_id: 'medium', label: 'Medium', target_host_lines: 20, is_default: true },
]

describe('LengthFieldset', () => {
  it('is a group of radios with a legend and the host lines of each', () => {
    render(<LengthFieldset lengths={lengths} value="medium" onChange={vi.fn()} />)

    expect(screen.getByRole('group', { name: 'Length' })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: /Medium.*20/ })).toBeChecked()
  })

  it('reports the chosen length', () => {
    const onChange = vi.fn()
    render(<LengthFieldset lengths={lengths} value="medium" onChange={onChange} />)

    fireEvent.click(screen.getByRole('radio', { name: /Short/ }))

    expect(onChange).toHaveBeenCalledWith('short')
  })
})
