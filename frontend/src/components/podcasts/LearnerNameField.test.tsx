import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import LearnerNameField from './LearnerNameField'

describe('LearnerNameField', () => {
  it('is a labelled input limited to forty characters', () => {
    render(<LearnerNameField value="Sam" onChange={vi.fn()} />)

    const input = screen.getByLabelText(/Your name/)
    expect(input).toHaveValue('Sam')
    expect(input).toHaveAttribute('maxLength', '40')
  })

  it('reports the typed name', () => {
    const onChange = vi.fn()
    render(<LearnerNameField value="" onChange={onChange} />)

    fireEvent.change(screen.getByLabelText(/Your name/), { target: { value: 'Ana' } })

    expect(onChange).toHaveBeenCalledWith('Ana')
  })
})
