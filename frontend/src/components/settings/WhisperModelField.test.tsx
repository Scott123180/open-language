import { render, screen, fireEvent, within } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import WhisperModelField from './WhisperModelField'

describe('WhisperModelField', () => {
  it('is a select labelled Speech Recognition Model showing the value', () => {
    render(<WhisperModelField value="small" onChange={vi.fn()} />)

    const select = screen.getByLabelText<HTMLSelectElement>('Speech Recognition Model')
    expect(select.value).toBe('small')
    expect(
      within(select)
        .getAllByRole('option')
        .map((o) => o.getAttribute('value'))
    ).toEqual(['base', 'small', 'medium'])
  })

  it('calls onChange with the chosen model', () => {
    const onChange = vi.fn()
    render(<WhisperModelField value="base" onChange={onChange} />)

    fireEvent.change(screen.getByLabelText('Speech Recognition Model'), {
      target: { value: 'medium' },
    })

    expect(onChange).toHaveBeenCalledWith('medium')
  })

  it('says when a change takes effect', () => {
    render(<WhisperModelField value="base" onChange={vi.fn()} />)

    expect(screen.getByText(/takes effect on next recording/i)).toBeInTheDocument()
  })
})
