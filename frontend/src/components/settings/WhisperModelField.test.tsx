import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { chooseOption, optionLabels } from '../shared/themedSelect.test.utils'
import WhisperModelField from './WhisperModelField'

describe('WhisperModelField', () => {
  it('is a drop-down labelled Speech Recognition Model showing the value', () => {
    render(<WhisperModelField value="small" onChange={vi.fn()} />)

    expect(screen.getByRole('combobox', { name: 'Speech Recognition Model' })).toHaveTextContent('Small — balanced')
    expect(optionLabels('Speech Recognition Model')).toEqual([
      'Base — fast, lower accuracy',
      'Small — balanced',
      'Medium — slower, higher accuracy',
    ])
  })

  it('calls onChange with the chosen model', () => {
    const onChange = vi.fn()
    render(<WhisperModelField value="base" onChange={onChange} />)

    chooseOption('Speech Recognition Model', 'Medium — slower, higher accuracy')

    expect(onChange).toHaveBeenCalledWith('medium')
  })

  it('says when a change takes effect', () => {
    render(<WhisperModelField value="base" onChange={vi.fn()} />)

    expect(screen.getByText(/takes effect on next recording/i)).toBeInTheDocument()
  })
})
