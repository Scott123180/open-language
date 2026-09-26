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
  whisper_model: 'base',
  correction_mode: 'off',
  updated_at: '2026-03-15T10:00:00Z',
}

const mockVoices: api.VoiceOption[] = [
  {
    key: 'es_ES-mls-medium',
    display_name: 'Marta (Spain)',
    gender: 'female',
    locale: 'es_ES',
    quality: 'medium',
    speaking_rate: 'natural',
  },
]

function renderSettings() {
  return render(
    <MemoryRouter>
      <Settings />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(api.getVoices).mockResolvedValue(mockVoices)
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
      expect(api.updateSettings).toHaveBeenCalledWith(
        expect.objectContaining({ llm_model: 'llama3.2', suggestion_count: 5 }),
      ),
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

describe('Settings page — correction mode', () => {
  it('renders the three correction modes as a labelled group', async () => {
    vi.mocked(api.getSettings).mockResolvedValue(mockSettings)
    renderSettings()

    const group = await screen.findByRole('group', { name: /correction/i })
    expect(group).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: /^off$/i })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: /gentle/i })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: /strict/i })).toBeInTheDocument()
  })

  it('defaults the selection to the loaded setting', async () => {
    vi.mocked(api.getSettings).mockResolvedValue({ ...mockSettings, correction_mode: 'gentle' })
    renderSettings()

    const gentle = await screen.findByRole<HTMLInputElement>('radio', { name: /gentle/i })
    expect(gentle.checked).toBe(true)
  })

  it('selects off when the stored mode is off', async () => {
    vi.mocked(api.getSettings).mockResolvedValue(mockSettings)
    renderSettings()

    const off = await screen.findByRole<HTMLInputElement>('radio', { name: /^off$/i })
    expect(off.checked).toBe(true)
  })

  it('submits the chosen mode', async () => {
    vi.mocked(api.getSettings).mockResolvedValue(mockSettings)
    vi.mocked(api.updateSettings).mockResolvedValue({ ...mockSettings, correction_mode: 'strict' })
    renderSettings()

    const strict = await screen.findByRole('radio', { name: /strict/i })
    fireEvent.click(strict)
    fireEvent.click(screen.getByRole('button', { name: /save/i }))

    await waitFor(() =>
      expect(api.updateSettings).toHaveBeenCalledWith(
        expect.objectContaining({ correction_mode: 'strict' }),
      ),
    )
  })

  it('exposes the performance hint to the group via aria-describedby', async () => {
    vi.mocked(api.getSettings).mockResolvedValue(mockSettings)
    renderSettings()

    const group = await screen.findByRole('group', { name: /correction/i })
    const describedBy = (group.getAttribute('aria-describedby') ?? '').split(/\s+/)
    expect(describedBy.length).toBeGreaterThan(0)
    const described = describedBy
      .map((id) => document.getElementById(id)?.textContent ?? '')
      .join(' ')
    expect(described).toMatch(/several seconds/i)
  })

  it('warns that a slow check is skipped so the conversation continues', async () => {
    vi.mocked(api.getSettings).mockResolvedValue(mockSettings)
    renderSettings()

    await screen.findByRole('group', { name: /correction/i })
    expect(screen.getByText(/skipped/i)).toBeInTheDocument()
  })
})

describe('Settings page — correction accuracy warning', () => {
  it('warns that corrections can be wrong', async () => {
    vi.mocked(api.getSettings).mockResolvedValue(mockSettings)
    renderSettings()

    await screen.findByRole('group', { name: /correction/i })
    expect(screen.getByText(/can be wrong/i)).toBeInTheDocument()
  })

  it('tells the learner to treat a correction as a prompt to check, not an authority', async () => {
    vi.mocked(api.getSettings).mockResolvedValue(mockSettings)
    renderSettings()

    await screen.findByRole('group', { name: /correction/i })
    expect(screen.getByText(/double-check/i)).toBeInTheDocument()
  })

  it('names the kind of model the accuracy depends on', async () => {
    vi.mocked(api.getSettings).mockResolvedValue(mockSettings)
    renderSettings()

    const warning = await screen.findByRole('note', { name: /correction accuracy/i })
    expect(warning).toHaveTextContent(/larger model/i)
  })

  it('exposes the warning to the group alongside the performance hint', async () => {
    vi.mocked(api.getSettings).mockResolvedValue(mockSettings)
    renderSettings()

    const group = await screen.findByRole('group', { name: /correction/i })
    const describedBy = (group.getAttribute('aria-describedby') ?? '').split(/\s+/)
    expect(describedBy.length).toBeGreaterThan(1)
    for (const id of describedBy) {
      expect(document.getElementById(id)).toBeInTheDocument()
    }
  })

  it('marks the warning as a note rather than plain prose', async () => {
    vi.mocked(api.getSettings).mockResolvedValue(mockSettings)
    renderSettings()

    await screen.findByRole('group', { name: /correction/i })
    expect(screen.getByRole('note', { name: /correction accuracy/i })).toBeInTheDocument()
  })

  it('uses no hardcoded hex colours in the warning', async () => {
    vi.mocked(api.getSettings).mockResolvedValue(mockSettings)
    renderSettings()

    const warning = await screen.findByRole('note', { name: /correction accuracy/i })
    expect(warning.getAttribute('style') ?? '').not.toMatch(/#[0-9a-f]{3,8}/i)
  })
})

