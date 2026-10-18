import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import SeriesExperimentalNote from './SeriesExperimentalNote'

describe('SeriesExperimentalNote', () => {
  it('says series are experimental and what can go wrong, as a note', () => {
    render(<SeriesExperimentalNote />)

    const note = screen.getByRole('note', { name: 'Series are experimental' })
    expect(note).toHaveTextContent('Series are experimental')
    expect(note).toHaveTextContent(/never said/)
    expect(note).toHaveTextContent(/earlier topic/)
  })
})
