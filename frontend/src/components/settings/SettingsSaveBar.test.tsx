import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import SettingsSaveBar from './SettingsSaveBar'

const idle = { isSaving: false, successMessage: null, errorMessage: null, onSave: vi.fn() }

describe('SettingsSaveBar', () => {
  it('shows the success message as a status', () => {
    render(<SettingsSaveBar {...idle} successMessage="Settings saved." />)

    expect(screen.getByRole('status')).toHaveTextContent('Settings saved.')
  })

  it('shows the error message as an alert', () => {
    render(<SettingsSaveBar {...idle} errorMessage="Server error" />)

    expect(screen.getByRole('alert')).toHaveTextContent('Server error')
  })

  it('shows neither message when idle', () => {
    render(<SettingsSaveBar {...idle} />)

    expect(screen.queryByRole('status')).not.toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('is the form submit button and calls onSave when pressed', () => {
    const onSave = vi.fn()
    render(<SettingsSaveBar {...idle} onSave={onSave} />)

    const button = screen.getByRole('button', { name: 'Save' })
    fireEvent.click(button)

    expect(button).toHaveAttribute('type', 'submit')
    expect(onSave).toHaveBeenCalledTimes(1)
  })

  it('is disabled and reads Saving… while saving', () => {
    render(<SettingsSaveBar {...idle} isSaving />)

    expect(screen.getByRole('button', { name: 'Saving…' })).toBeDisabled()
  })
})
