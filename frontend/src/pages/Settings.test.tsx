import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import Settings from './Settings'
import * as api from '../services/api'

vi.mock('../services/api')

const mockSettings: api.AppSettings = {
  llm_model: 'llama3.1',
  target_language: 'es',
  native_language: 'en',
  tts_voice: 'es_ES-mls-medium',
  suggestion_count: 3,
  updated_at: '2026-03-15T10:00:00Z',
}

function renderSettings() {
  return render(
    <MemoryRouter>
      <Settings />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.resetAllMocks()
})

describe('Settings page', () => {
  it('renders with current settings loaded', async () => {
    vi.mocked(api.getSettings).mockResolvedValue(mockSettings)
    renderSettings()
    await waitFor(() => expect(screen.getByLabelText(/llm model/i)).toBeInTheDocument())
    expect(screen.getByLabelText(/suggestion count/i)).toBeInTheDocument()
  })

  it('shows model selector with current llm_model value', async () => {
    vi.mocked(api.getSettings).mockResolvedValue(mockSettings)
    renderSettings()
    const select = await screen.findByLabelText<HTMLSelectElement>(/llm model/i)
    expect(select.value).toBe('llama3.1')
  })

  it('shows suggestion count input with current value', async () => {
    vi.mocked(api.getSettings).mockResolvedValue(mockSettings)
    renderSettings()
    const input = await screen.findByLabelText<HTMLInputElement>(/suggestion count/i)
    expect(input.value).toBe('3')
  })

  it('"Save" button calls api.updateSettings with updated values', async () => {
    vi.mocked(api.getSettings).mockResolvedValue(mockSettings)
    vi.mocked(api.updateSettings).mockResolvedValue({ ...mockSettings, llm_model: 'llama3.2', suggestion_count: 5 })
    renderSettings()

    const select = await screen.findByLabelText<HTMLSelectElement>(/llm model/i)
    fireEvent.change(select, { target: { value: 'llama3.2' } })

    const input = screen.getByLabelText<HTMLInputElement>(/suggestion count/i)
    fireEvent.change(input, { target: { value: '5' } })

    fireEvent.click(screen.getByRole('button', { name: /save/i }))

    await waitFor(() =>
      expect(api.updateSettings).toHaveBeenCalledWith({
        llm_model: 'llama3.2',
        suggestion_count: 5,
      }),
    )
  })

  it('shows success message after save', async () => {
    vi.mocked(api.getSettings).mockResolvedValue(mockSettings)
    vi.mocked(api.updateSettings).mockResolvedValue(mockSettings)
    renderSettings()

    await screen.findByRole('button', { name: /save/i })
    fireEvent.click(screen.getByRole('button', { name: /save/i }))

    await waitFor(() => expect(screen.getByRole('status')).toBeInTheDocument())
    expect(screen.getByText(/settings saved/i)).toBeInTheDocument()
  })

  it('shows error message on save failure', async () => {
    vi.mocked(api.getSettings).mockResolvedValue(mockSettings)
    vi.mocked(api.updateSettings).mockRejectedValue(new Error('Server error'))
    renderSettings()

    await screen.findByRole('button', { name: /save/i })
    fireEvent.click(screen.getByRole('button', { name: /save/i }))

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
    expect(screen.getByText(/server error/i)).toBeInTheDocument()
  })
})
