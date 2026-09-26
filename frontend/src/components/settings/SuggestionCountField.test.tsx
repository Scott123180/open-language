import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import SuggestionCountField from './SuggestionCountField'

describe('SuggestionCountField', () => {
  it('is a number input labelled Suggestion Count showing the value', () => {
    render(<SuggestionCountField value={3} onChange={vi.fn()} />)

    const input = screen.getByLabelText<HTMLInputElement>(/suggestion count/i)
    expect([input.type, input.value, input.min, input.max]).toEqual(['number', '3', '1', '5'])
  })

  it('calls onChange with the number entered', () => {
    const onChange = vi.fn()
    render(<SuggestionCountField value={3} onChange={onChange} />)

    fireEvent.change(screen.getByLabelText(/suggestion count/i), { target: { value: '5' } })

    expect(onChange).toHaveBeenCalledWith(5)
  })
})
