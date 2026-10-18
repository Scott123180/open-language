import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import EpisodeKindFieldset from './EpisodeKindFieldset'

describe('EpisodeKindFieldset', () => {
  it('offers the next series episode and a one-off, as two choice tiles', () => {
    render(<EpisodeKindFieldset nextEpisodeNumber={3} value="series" onChange={vi.fn()} />)

    expect(screen.getByRole('group', { name: 'Episode' })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: /Episode 3/ })).toBeChecked()
    expect(screen.getByRole('radio', { name: /One-off episode/ })).not.toBeChecked()
  })

  it('reports the chosen kind', () => {
    const onChange = vi.fn()
    render(<EpisodeKindFieldset nextEpisodeNumber={3} value="series" onChange={onChange} />)

    fireEvent.click(screen.getByRole('radio', { name: /One-off episode/ }))

    expect(onChange).toHaveBeenCalledWith('one_off')
  })
})
