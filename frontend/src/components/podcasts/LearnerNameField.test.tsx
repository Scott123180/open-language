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

describe('LearnerNameField — a series host with the same name (010)', () => {
  it('points out the clash, read with the field', () => {
    render(<LearnerNameField value="hugo" onChange={vi.fn()} hostNames={['Hugo', 'Inés']} />)

    const hint = screen.getByRole('status')
    expect(hint).toHaveTextContent('Hugo has the same name as you. Change the name the hosts call you.')
    expect(screen.getByLabelText(/Your name/).getAttribute('aria-describedby')).toContain(hint.id)
  })

  it('says nothing without a clash', () => {
    render(<LearnerNameField value="Sam" onChange={vi.fn()} hostNames={['Hugo', 'Inés']} />)

    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })
})
