import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import FeedbackNote from './FeedbackNote'
import type { FeedbackNoteData } from '../../services/api'

const correction: FeedbackNoteData = {
  id: 7,
  message_id: 10,
  kind: 'correction',
  category: 'conjugation',
  error_fragment: 'Yo tener',
  corrected_text: 'Yo tengo veinte años',
  explanation: '"Tener" needs to be conjugated: with "yo" it becomes "tengo".',
  mode: 'strict',
  rank: 0,
  created_at: '2026-03-20T10:04:11Z',
}

const repeatRequest: FeedbackNoteData = {
  ...correction,
  id: 8,
  kind: 'repeat_request',
  category: null,
  error_fragment: null,
  corrected_text: null,
  explanation: "I didn't quite catch that — could you say it again?",
}

describe('FeedbackNote — correction', () => {
  it('renders the learner error fragment', () => {
    render(<FeedbackNote note={correction} />)
    expect(screen.getByText(/Yo tener/)).toBeInTheDocument()
  })

  it('renders the corrected sentence', () => {
    render(<FeedbackNote note={correction} />)
    expect(screen.getByText('Yo tengo veinte años')).toBeInTheDocument()
  })

  it('renders the explanation', () => {
    render(<FeedbackNote note={correction} />)
    expect(screen.getByText(/needs to be conjugated/)).toBeInTheDocument()
  })

  it('is marked as a note rather than dialogue', () => {
    render(<FeedbackNote note={correction} />)
    expect(screen.getByRole('note')).toBeInTheDocument()
  })

  it('carries an accessible label identifying it as learning feedback', () => {
    render(<FeedbackNote note={correction} />)
    expect(screen.getByRole('note')).toHaveAccessibleName(/learning feedback/i)
  })

  it('uses no hardcoded hex colours', () => {
    const { container } = render(<FeedbackNote note={correction} />)
    expect(container.innerHTML).not.toMatch(/#[0-9a-f]{3,8}\b/i)
  })

  it('names the error category', () => {
    render(<FeedbackNote note={correction} />)
    expect(screen.getByText(/conjugation/i)).toBeInTheDocument()
  })
})

describe('FeedbackNote — repeat request', () => {
  it('renders the ask-to-repeat text', () => {
    render(<FeedbackNote note={repeatRequest} />)
    expect(screen.getByText(/could you say it again/i)).toBeInTheDocument()
  })

  it('renders no corrected sentence', () => {
    render(<FeedbackNote note={repeatRequest} />)
    expect(screen.queryByText('Yo tengo veinte años')).not.toBeInTheDocument()
  })

  it('is still marked as a note', () => {
    render(<FeedbackNote note={repeatRequest} />)
    expect(screen.getByRole('note')).toHaveAccessibleName(/learning feedback/i)
  })
})
