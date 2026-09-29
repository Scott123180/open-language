import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import FormatFieldset from './FormatFieldset'
import type { PodcastFormatOption } from '../../services/podcastsApi'

const formats: PodcastFormatOption[] = [
  { format_id: 'one_host', label: 'One host', host_count: 1, is_learner_speaking: true, description: 'You and one host.' },
  { format_id: 'panel', label: 'Panel', host_count: 2, is_learner_speaking: true, description: 'You and two hosts.' },
]

describe('FormatFieldset', () => {
  it('is a group of radios with a legend', () => {
    render(<FormatFieldset formats={formats} value="panel" onChange={vi.fn()} />)

    expect(screen.getByRole('group', { name: 'Format' })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: /Panel/ })).toBeChecked()
    expect(screen.getByRole('radio', { name: /One host/ })).not.toBeChecked()
  })

  it('reports the chosen format', () => {
    const onChange = vi.fn()
    render(<FormatFieldset formats={formats} value="panel" onChange={onChange} />)

    fireEvent.click(screen.getByRole('radio', { name: /One host/ }))

    expect(onChange).toHaveBeenCalledWith('one_host')
  })
})
