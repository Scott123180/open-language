import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ConversationLevelFieldset from './ConversationLevelFieldset'
import * as api from '../../services/api'

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

function renderFieldset(value: api.ConversationLevelId = 'natural') {
  const onChange = vi.fn()
  render(<ConversationLevelFieldset levels={levels} value={value} onChange={onChange} />)
  return onChange
}

beforeEach(() => {
  vi.resetAllMocks()
})

describe('ConversationLevelFieldset', () => {
  it('is a group with the legend Conversation level', () => {
    renderFieldset()

    expect(screen.getByRole('group', { name: 'Conversation level' })).toBeInTheDocument()
  })

  it('renders one radio per level in the given order', () => {
    renderFieldset()

    expect(screen.getAllByRole('radio').map((radio) => radio.getAttribute('value'))).toEqual([
      'beginner',
      'elementary',
      'intermediate',
      'natural',
    ])
  })

  it('names each radio with its label and CEFR label', () => {
    renderFieldset()

    const beginner = screen.getByRole('radio', { name: /beginner/i })
    expect(beginner).toHaveAccessibleName(expect.stringContaining('Beginner'))
    expect(beginner).toHaveAccessibleName(expect.stringContaining('A1'))
    expect(screen.getByRole('radio', { name: /natural/i })).toHaveAccessibleName(
      expect.stringContaining('No limit')
    )
  })

  it('describes each radio with its level description', () => {
    renderFieldset()

    expect(screen.getByRole('radio', { name: /beginner/i })).toHaveAccessibleDescription(
      levels[0].description
    )
  })

  it('checks the radio matching the value', () => {
    renderFieldset('elementary')

    expect(screen.getByRole('radio', { name: /elementary/i })).toBeChecked()
    expect(screen.getByRole('radio', { name: /natural/i })).not.toBeChecked()
  })

  it('calls onChange with the chosen level id', () => {
    const onChange = renderFieldset('natural')

    fireEvent.click(screen.getByRole('radio', { name: /beginner/i }))

    expect(onChange).toHaveBeenCalledWith('beginner')
  })

  it('never calls the API itself', () => {
    const onChange = renderFieldset('natural')

    fireEvent.click(screen.getByRole('radio', { name: /intermediate/i }))

    expect(onChange).toHaveBeenCalled()
    expect(api.updateSettings).not.toHaveBeenCalled()
    expect(api.getSettings).not.toHaveBeenCalled()
  })

  it('warns that levels are experimental and the model may not keep to them', () => {
    renderFieldset()

    const warning = screen.getByRole('note', { name: /level accuracy/i })
    expect(warning).toHaveTextContent(/experimental/i)
    expect(warning).toHaveTextContent(/does not always keep to the level/i)
    expect(warning).toHaveTextContent(/larger model/i)
  })

  it('ties the warning to the level group', () => {
    renderFieldset()

    const group = screen.getByRole('group', { name: 'Conversation level' })
    const warning = screen.getByRole('note', { name: /level accuracy/i })
    expect(group.getAttribute('aria-describedby')).toBe(warning.id)
  })

  it('titles the warning in the warning text colour, which keeps AA contrast in light theme', () => {
    renderFieldset()

    const title = screen.getByText('Levels are experimental')
    expect(title.getAttribute('style')).toContain('var(--color-warning-text)')
  })

  it('uses no hardcoded hex colours in the warning', () => {
    renderFieldset()

    const warning = screen.getByRole('note', { name: /level accuracy/i })
    expect(warning.getAttribute('style') ?? '').not.toMatch(/#[0-9a-f]{3,8}/i)
  })
})
