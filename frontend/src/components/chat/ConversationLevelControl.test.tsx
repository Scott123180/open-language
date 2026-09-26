import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as api from '../../services/api'
import ConversationLevelControl from './ConversationLevelControl'

vi.mock('../../services/api')

const levels: api.ConversationLevelOption[] = [
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

const levelSelect = () => screen.findByRole<HTMLSelectElement>('combobox', { name: 'Level' })

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(api.getSettings).mockResolvedValue({
    conversation_level: 'intermediate',
  } as api.AppSettings)
  vi.mocked(api.getConversationLevels).mockResolvedValue(levels)
})

describe('ConversationLevelControl', () => {
  it('is a native select named Level', async () => {
    render(<ConversationLevelControl />)

    expect((await levelSelect()).tagName).toBe('SELECT')
  })

  it('reads each option as its label and CEFR level, and Natural alone', async () => {
    render(<ConversationLevelControl />)

    const options = within(await levelSelect()).getAllByRole('option')
    expect(options.map((option) => option.textContent)).toEqual([
      'Beginner (A1)',
      'Elementary (A2)',
      'Intermediate (B1)',
      'Natural',
    ])
  })

  it('shows the stored level', async () => {
    render(<ConversationLevelControl />)

    await waitFor(async () => expect((await levelSelect()).value).toBe('intermediate'))
  })

  it("is described by the selected level's description, which follows the selection", async () => {
    vi.mocked(api.updateSettings).mockResolvedValue({} as api.AppSettings)
    render(<ConversationLevelControl />)
    const select = await levelSelect()
    await waitFor(() => expect(select).toHaveAccessibleDescription(levels[2].description))

    fireEvent.change(select, { target: { value: 'beginner' } })

    expect(select).toHaveAccessibleDescription(levels[0].description)
  })

  it('is disabled while saving, and announces the change politely once saved', async () => {
    let finish: (settings: api.AppSettings) => void = () => {}
    vi.mocked(api.updateSettings).mockReturnValue(new Promise((resolve) => (finish = resolve)))
    render(<ConversationLevelControl />)
    const select = await levelSelect()

    fireEvent.change(select, { target: { value: 'beginner' } })
    expect(select).toBeDisabled()
    finish({} as api.AppSettings)

    const status = await screen.findByText('Level set to Beginner. It applies from the next reply.')
    expect(status).toHaveAttribute('aria-live', 'polite')
    expect(select).toBeEnabled()
  })

  it('shows a failed save as an alert and reverts', async () => {
    vi.mocked(api.updateSettings).mockRejectedValue(new Error('HTTP 500'))
    render(<ConversationLevelControl />)
    const select = await levelSelect()
    await waitFor(() => expect(select.value).toBe('intermediate'))

    fireEvent.change(select, { target: { value: 'beginner' } })

    expect(await screen.findByRole('alert')).toHaveTextContent(/level was not changed/i)
    expect(select.value).toBe('intermediate')
  })

  it('renders nothing until the level list loads', () => {
    vi.mocked(api.getConversationLevels).mockReturnValue(new Promise(() => {}))

    render(<ConversationLevelControl />)

    expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
  })

  it('shows an alert instead of the control when the level cannot be loaded', async () => {
    vi.mocked(api.getSettings).mockRejectedValue(new Error('offline'))

    render(<ConversationLevelControl />)

    expect(await screen.findByRole('alert')).toHaveTextContent(/could not be loaded/i)
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
  })

  it('uses design tokens rather than hex colours', async () => {
    render(<ConversationLevelControl />)

    expect((await levelSelect()).getAttribute('style') ?? '').not.toMatch(/#[0-9a-f]{3,8}/i)
  })
})
