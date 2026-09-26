import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import Settings from './Settings'
import * as api from '../services/api'

vi.mock('../services/api')

const mockSettings: api.AppSettings = {
  llm_provider: 'ollama',
  llm_model: 'llama3.1',
  llm_effort: 'low',
  target_language: 'es',
  native_language: 'en',
  tts_voice: 'es_ES-mls-medium',
  suggestion_count: 3,
  whisper_model: 'base',
  correction_mode: 'off',
  conversation_level: 'natural',
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

const mockProviders: api.LlmProviderOption[] = [
  {
    provider_id: 'ollama',
    display_name: 'Ollama (local)',
    is_local: true,
    models: [
      { model_id: 'llama3.1:8b', label: 'llama3.1:8b' },
      { model_id: 'llama3.2', label: 'llama3.2' },
    ],
    default_model: 'llama3.1:8b',
    effort_levels: [],
    default_effort: null,
    privacy_notice: null,
    is_available: true,
    unavailable_reason: null,
    unavailable_message: null,
  },
  {
    provider_id: 'claude',
    display_name: 'Claude (via Claude Code)',
    is_local: false,
    models: [{ model_id: 'sonnet', label: 'Claude Sonnet' }],
    default_model: 'sonnet',
    effort_levels: [{ effort_id: 'low', label: 'Low — fastest replies' }],
    default_effort: 'low',
    privacy_notice:
      "Your conversation text is sent to Anthropic under your Claude account and counts toward your Claude plan's usage. Your voice recordings and audio stay on your computer.",
    is_available: true,
    unavailable_reason: null,
    unavailable_message: null,
  },
]

const mockLevels: api.ConversationLevelOption[] = [
  {
    level_id: 'beginner',
    label: 'Beginner',
    cefr_label: 'A1',
    description: 'Very short, simple sentences — like talking with a young child.',
  },
  {
    level_id: 'elementary',
    label: 'Elementary',
    cefr_label: 'A2',
    description: 'Short, clear sentences with everyday words — like talking with a patient friend.',
  },
  {
    level_id: 'intermediate',
    label: 'Intermediate',
    cefr_label: 'B1',
    description: 'Connected, everyday speech from a clear, considerate adult — no rare words.',
  },
  {
    level_id: 'natural',
    label: 'Natural',
    cefr_label: 'No limit',
    description: 'Ordinary everyday native speech, with no limits.',
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
  vi.mocked(api.getLlmProviders).mockResolvedValue(mockProviders)
  vi.mocked(api.getConversationLevels).mockResolvedValue(mockLevels)
})

describe('Settings page', () => {
  it('renders with current settings loaded', async () => {
    vi.mocked(api.getSettings).mockResolvedValue(mockSettings)
    renderSettings()
    await waitFor(() => expect(screen.getByLabelText('Model')).toBeInTheDocument())
    expect(screen.getByLabelText(/suggestion count/i)).toBeInTheDocument()
  })

  it('shows model selector with current llm_model value', async () => {
    vi.mocked(api.getSettings).mockResolvedValue(mockSettings)
    renderSettings()
    const select = await screen.findByLabelText<HTMLSelectElement>('Model')
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

    const select = await screen.findByLabelText<HTMLSelectElement>('Model')
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

describe('Settings page — language model provider', () => {
  it('loads the provider catalogue and renders the provider fields', async () => {
    vi.mocked(api.getSettings).mockResolvedValue(mockSettings)
    renderSettings()

    const group = await screen.findByRole('group', { name: /language model/i })
    expect(api.getLlmProviders).toHaveBeenCalled()
    expect(group).toContainElement(screen.getByRole('radio', { name: 'Ollama (local)' }))
  })

  it('no longer renders the old hard-coded model list', async () => {
    vi.mocked(api.getSettings).mockResolvedValue(mockSettings)
    renderSettings()

    const select = await screen.findByLabelText('Model')
    const options = Array.from(select.querySelectorAll('option')).map((o) => o.textContent)
    expect(options).not.toContain('mistral')
  })

  it('saves the provider, model, and effort together', async () => {
    vi.mocked(api.getSettings).mockResolvedValue(mockSettings)
    vi.mocked(api.updateSettings).mockResolvedValue(mockSettings)
    renderSettings()

    fireEvent.click(await screen.findByRole('radio', { name: 'Claude (via Claude Code)' }))
    fireEvent.click(screen.getByRole('button', { name: /save/i }))

    await waitFor(() =>
      expect(api.updateSettings).toHaveBeenCalledWith(
        expect.objectContaining({ llm_provider: 'claude', llm_model: 'sonnet', llm_effort: 'low' }),
      ),
    )
  })

  it('shows a rejected save and keeps the learner\'s choice', async () => {
    const detail = 'Sign in to Claude Code (run `claude` in a terminal) to use Claude.'
    vi.mocked(api.getSettings).mockResolvedValue(mockSettings)
    vi.mocked(api.updateSettings).mockRejectedValue(new Error(detail))
    renderSettings()

    fireEvent.click(await screen.findByRole('radio', { name: 'Claude (via Claude Code)' }))
    fireEvent.click(screen.getByRole('button', { name: /save/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(detail)
    expect(screen.getByRole('radio', { name: 'Claude (via Claude Code)' })).toBeChecked()
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

describe('Settings page — provider-neutral correction warning', () => {
  it('no longer blames a local model for false flags', async () => {
    vi.mocked(api.getSettings).mockResolvedValue(mockSettings)
    renderSettings()

    const warning = await screen.findByRole('note', { name: /correction accuracy/i })
    expect(warning).not.toHaveTextContent(/local model/i)
  })

  it('keeps the false-flag caveat', async () => {
    vi.mocked(api.getSettings).mockResolvedValue(mockSettings)
    renderSettings()

    const warning = await screen.findByRole('note', { name: /correction accuracy/i })
    expect(warning).toHaveTextContent(/flags sentences that were already correct/i)
  })
})

describe('Settings page — conversation level', () => {
  it('renders the four levels from the catalogue in a Conversation level group', async () => {
    vi.mocked(api.getSettings).mockResolvedValue(mockSettings)
    renderSettings()

    const group = await screen.findByRole('group', { name: 'Conversation level' })
    const radios = within(group).getAllByRole('radio')
    expect(radios.map((radio) => radio.getAttribute('value'))).toEqual([
      'beginner',
      'elementary',
      'intermediate',
      'natural',
    ])
  })

  it('checks the stored level', async () => {
    vi.mocked(api.getSettings).mockResolvedValue({
      ...mockSettings,
      conversation_level: 'intermediate',
    })
    renderSettings()

    expect(await screen.findByRole('radio', { name: /intermediate/i })).toBeChecked()
  })

  it('saves the chosen level in the same call as the other fields', async () => {
    vi.mocked(api.getSettings).mockResolvedValue(mockSettings)
    vi.mocked(api.updateSettings).mockResolvedValue(mockSettings)
    renderSettings()

    fireEvent.click(await screen.findByRole('radio', { name: /elementary/i }))
    fireEvent.click(screen.getByRole('button', { name: /save/i }))

    await waitFor(() => expect(api.updateSettings).toHaveBeenCalledTimes(1))
    expect(api.updateSettings).toHaveBeenCalledWith(
      expect.objectContaining({
        conversation_level: 'elementary',
        correction_mode: 'off',
        suggestion_count: 3,
      })
    )
  })

  it('sits directly before the correction feedback group', async () => {
    vi.mocked(api.getSettings).mockResolvedValue(mockSettings)
    renderSettings()

    const level = await screen.findByRole('group', { name: 'Conversation level' })
    const correction = screen.getByRole('group', { name: /correction/i })
    expect(level.nextElementSibling).toBe(correction)
  })

  it('replaces the level group with an explanation when the catalogue fails to load', async () => {
    vi.mocked(api.getSettings).mockResolvedValue(mockSettings)
    vi.mocked(api.getConversationLevels).mockRejectedValue(new Error('HTTP 500'))
    renderSettings()

    await screen.findByRole('group', { name: /correction/i })
    expect(screen.queryByRole('group', { name: 'Conversation level' })).not.toBeInTheDocument()
    expect(await screen.findByRole('alert')).toHaveTextContent(
      /conversation levels could not be loaded.*reload/i
    )
  })
})
