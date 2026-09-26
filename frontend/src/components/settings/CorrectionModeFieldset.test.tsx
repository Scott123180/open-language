import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import CorrectionModeFieldset from './CorrectionModeFieldset'
import type { CorrectionMode } from '../../services/api'

function renderFieldset(value: CorrectionMode = 'off') {
  const onChange = vi.fn()
  render(<CorrectionModeFieldset value={value} onChange={onChange} />)
  return onChange
}

describe('CorrectionModeFieldset', () => {
  it('renders the three modes in a group labelled Correction Feedback', () => {
    renderFieldset()

    const group = screen.getByRole('group', { name: 'Correction Feedback' })
    expect(group).toContainElement(screen.getByRole('radio', { name: /^off$/i }))
    expect(screen.getAllByRole('radio').map((radio) => radio.getAttribute('value'))).toEqual([
      'off',
      'gentle',
      'strict',
    ])
  })

  it('checks the radio matching the value', () => {
    renderFieldset('gentle')

    expect(screen.getByRole('radio', { name: /gentle/i })).toBeChecked()
    expect(screen.getByRole('radio', { name: /^off$/i })).not.toBeChecked()
  })

  it('calls onChange with the chosen mode', () => {
    const onChange = renderFieldset('off')

    fireEvent.click(screen.getByRole('radio', { name: /strict/i }))

    expect(onChange).toHaveBeenCalledWith('strict')
  })

  it('describes each mode on its radio', () => {
    renderFieldset()

    expect(screen.getByRole('radio', { name: /gentle/i })).toHaveAccessibleDescription(
      /restates your sentence/i
    )
  })

  it('shows the experimental warning as a note linked to the group', () => {
    renderFieldset()

    const warning = screen.getByRole('note', { name: /correction accuracy/i })
    expect(warning).toHaveTextContent('Corrections are experimental')
    const describedBy = screen.getByRole('group').getAttribute('aria-describedby') ?? ''
    expect(describedBy.split(' ')).toContain(warning.id)
  })
})
