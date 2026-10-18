import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import FavouriteToggle from './FavouriteToggle'

describe('FavouriteToggle', () => {
  it('is a pressed-or-not button named after the show', () => {
    const onToggle = vi.fn()
    render(<FavouriteToggle title="Big Little Questions" isFavourite onToggle={onToggle} />)

    const toggle = screen.getByRole('button', { name: 'Favourite Big Little Questions' })
    expect(toggle).toHaveAttribute('aria-pressed', 'true')
    fireEvent.click(toggle)
    expect(onToggle).toHaveBeenCalled()
  })

  it('is not pressed when the show is not a favourite', () => {
    render(<FavouriteToggle title="Game Day" isFavourite={false} onToggle={vi.fn()} />)

    expect(screen.getByRole('button', { name: 'Favourite Game Day' })).toHaveAttribute('aria-pressed', 'false')
  })
})
