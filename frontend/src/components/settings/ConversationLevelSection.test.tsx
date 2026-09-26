import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as api from '../../services/api'
import ConversationLevelSection from './ConversationLevelSection'

vi.mock('../../services/api')

const levels: api.ConversationLevelOption[] = [
  {
    level_id: 'beginner',
    label: 'Beginner',
    cefr_label: 'A1',
    description: 'Very short, simple sentences — like talking with a young child.',
  },
  {
    level_id: 'natural',
    label: 'Natural',
    cefr_label: 'No limit',
    description: 'Ordinary everyday native speech, with no limits.',
  },
]

const renderSection = () => render(<ConversationLevelSection value="natural" onChange={vi.fn()} />)

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(api.getConversationLevels).mockResolvedValue(levels)
})

describe('ConversationLevelSection', () => {
  it('shows the level group once the catalogue loads', async () => {
    renderSection()

    expect(await screen.findByRole('group', { name: 'Conversation level' })).toBeInTheDocument()
    expect(screen.getAllByRole('radio')).toHaveLength(levels.length)
  })

  it('shows nothing while the catalogue is loading', () => {
    vi.mocked(api.getConversationLevels).mockReturnValue(new Promise(() => {}))

    const { container } = renderSection()

    expect(container).toBeEmptyDOMElement()
  })

  it('explains what to do when the catalogue cannot be loaded', async () => {
    vi.mocked(api.getConversationLevels).mockRejectedValue(new Error('HTTP 500'))

    renderSection()

    expect(await screen.findByRole('alert')).toHaveTextContent(/could not be loaded.*reload/i)
    expect(screen.queryByRole('group')).not.toBeInTheDocument()
  })
})
