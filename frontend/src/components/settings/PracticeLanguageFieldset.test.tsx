import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import PracticeLanguageFieldset from './PracticeLanguageFieldset'
import type { PracticeLanguageOption } from '../../services/api'

const language = (language_id: string, display_name: string): PracticeLanguageOption => ({
  language_id,
  display_name,
  is_default: language_id === 'es',
  default_voice: `${language_id}-voice`,
  selected_voice: `${language_id}-voice`,
  is_voice_installed: true,
  voice_unavailable_message: null,
})
const languages = [language('es', 'Spanish'), language('de', 'German')]

function renderFieldset(value = 'es') {
  const onChange = vi.fn()
  render(<PracticeLanguageFieldset languages={languages} value={value} onChange={onChange} />)
  return onChange
}

describe('PracticeLanguageFieldset', () => {
  it('is a group labelled Practice language with one radio per language', () => {
    renderFieldset()

    const group = screen.getByRole('group', { name: 'Practice language' })
    expect(group).toContainElement(screen.getByRole('radio', { name: 'Spanish' }))
    expect(screen.getAllByRole('radio').map((radio) => radio.getAttribute('value'))).toEqual([
      'es',
      'de',
    ])
  })

  it('checks the radio matching the value', () => {
    renderFieldset('de')

    expect(screen.getByRole('radio', { name: 'German' })).toBeChecked()
    expect(screen.getByRole('radio', { name: 'Spanish' })).not.toBeChecked()
  })

  it('calls onChange with the chosen language id', () => {
    const onChange = renderFieldset('es')

    fireEvent.click(screen.getByRole('radio', { name: 'German' }))

    expect(onChange).toHaveBeenCalledWith('de')
  })

  it('explains that existing conversations keep their language', () => {
    renderFieldset()

    expect(screen.getByRole('group')).toHaveAccessibleDescription(
      /new conversations use this language.*existing conversations keep theirs/i,
    )
  })
})
