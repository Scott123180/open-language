import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { chooseOption, optionLabels } from '../shared/themedSelect.test.utils'
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
  it('is a drop-down labelled Voice listing the voices and showing the value', () => {
    render(<TtsVoiceField value="es_MX-claude-high" voices={voices} onChange={vi.fn()} />)

    expect(screen.getByRole('combobox', { name: 'Voice' })).toHaveTextContent('Claude (Mexico)')
    expect(optionLabels('Voice')).toEqual(['Marta (Spain)', 'Claude (Mexico)'])
  })

  it('calls onChange with the chosen voice', () => {
    const onChange = vi.fn()
    render(<TtsVoiceField value="es_ES-mls-medium" voices={voices} onChange={onChange} />)

    chooseOption('Voice', 'Claude (Mexico)')

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

describe('TtsVoiceField — a voice that is not installed (006 US4)', () => {
  const missing: VoiceOption[] = [
    { ...voices[0], is_installed: true },
    { ...voices[1], is_installed: false },
  ]

  it('shows how to install the selected voice, as a status', () => {
    render(<TtsVoiceField value="es_MX-claude-high" voices={missing} onChange={vi.fn()} />)

    expect(screen.getByRole('status')).toHaveTextContent(
      'Not installed. Run ./run.sh --setup to download it.',
    )
  })

  it('links the hint to the select', () => {
    render(<TtsVoiceField value="es_MX-claude-high" voices={missing} onChange={vi.fn()} />)

    expect(screen.getByLabelText('Voice')).toHaveAccessibleDescription(/not installed/i)
  })

  it('shows no hint for an installed voice', () => {
    render(<TtsVoiceField value="es_ES-mls-medium" voices={missing} onChange={vi.fn()} />)

    expect(screen.queryByRole('status')).toBeNull()
  })
})
