import { fireEvent, render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import TodaySubjectField from './TodaySubjectField'

describe('TodaySubjectField (011 FR-010)', () => {
  it('is a 120-character textbox with a live count', () => {
    render(<TodaySubjectField value="why we yawn" maxLength={120} onChange={vi.fn()} error={null} />)

    const box = screen.getByRole('textbox', { name: "Today's subject (optional)" })
    expect(box).toHaveAttribute('maxlength', '120')
    expect(screen.getByText('11 / 120')).toBeInTheDocument()
  })

  it('reports what is typed', () => {
    const onChange = vi.fn()
    render(<TodaySubjectField value="" maxLength={120} onChange={onChange} error={null} />)

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'el pan' } })

    expect(onChange).toHaveBeenCalledWith('el pan')
  })

  it('shows a declined subject beside the field', () => {
    render(<TodaySubjectField value="x" maxLength={120} onChange={vi.fn()} error="That subject can't be used." />)

    expect(screen.getByText("That subject can't be used.")).toBeInTheDocument()
    expect(screen.getByRole('textbox')).toHaveAttribute('aria-invalid', 'true')
  })
})
