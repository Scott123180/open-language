import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import ShowTextSwitch from './ShowTextSwitch'

describe('ShowTextSwitch', () => {
  it('is a labelled switch reflecting the preference', () => {
    render(<ShowTextSwitch isOn onChange={vi.fn()} />)

    expect(screen.getByRole('switch', { name: 'Show text' })).toBeChecked()
  })

  it('reports the new setting', () => {
    const onChange = vi.fn()
    render(<ShowTextSwitch isOn={false} onChange={onChange} />)

    fireEvent.click(screen.getByRole('switch', { name: 'Show text' }))

    expect(onChange).toHaveBeenCalledWith(true)
  })
})
