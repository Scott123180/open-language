import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import TtsVoiceField from './TtsVoiceField'
import type { VoiceOption } from '../../services/api'

const voices: VoiceOption[] = [
  {
    key: 'es_ES-mls-medium',
    display_name: 'Marta (Spain)',
    gender: 'female',
    locale: 'es_ES',
    quality: 'medium',
    speaking_rate: 'slow',
    language: 'es',
    is_installed: true,
  },
  {
    key: 'es_MX-claude-high',
    display_name: 'Claude (Mexico)',
    gender: 'male',
    locale: 'es_MX',
    quality: 'high',
    speaking_rate: 'fast',
    language: 'es',
    is_installed: true,
  },
]

describe('TtsVoiceField', () => {
  it('is a select labelled Voice listing the voices and showing the value', () => {
    render(<TtsVoiceField value="es_MX-claude-high" voices={voices} onChange={vi.fn()} />)

    const select = screen.getByLabelText<HTMLSelectElement>('Voice')
    expect(select.value).toBe('es_MX-claude-high')
    expect(screen.getByRole('option', { name: 'Marta (Spain)' })).toBeInTheDocument()
  })

  it('calls onChange with the chosen voice', () => {
    const onChange = vi.fn()
    render(<TtsVoiceField value="es_ES-mls-medium" voices={voices} onChange={onChange} />)

    fireEvent.change(screen.getByLabelText('Voice'), { target: { value: 'es_MX-claude-high' } })

    expect(onChange).toHaveBeenCalledWith('es_MX-claude-high')
  })

  it('describes the selected voice: gender, country, quality and pace', () => {
    render(<TtsVoiceField value="es_ES-mls-medium" voices={voices} onChange={vi.fn()} />)

    expect(screen.getByText(/♀ Female · Spain · Medium quality/)).toBeInTheDocument()
    expect(screen.getByText(/ideal for beginners/i)).toBeInTheDocument()
  })

  it('shows no description when the value matches no voice', () => {
    render(<TtsVoiceField value="" voices={voices} onChange={vi.fn()} />)

    expect(screen.queryByText(/quality/i)).not.toBeInTheDocument()
  })
})
