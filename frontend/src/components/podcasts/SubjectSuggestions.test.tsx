import { fireEvent, render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import SubjectSuggestions from './SubjectSuggestions'

const base = { phase: 'idle' as const, subjects: [] as string[], message: null as string | null, ask: vi.fn(), onChoose: vi.fn() }

describe('SubjectSuggestions (011 contracts §11)', () => {
  it('offers a secondary Suggest subjects button', () => {
    const ask = vi.fn()
    render(<SubjectSuggestions {...base} ask={ask} />)

    fireEvent.click(screen.getByRole('button', { name: 'Suggest subjects' }))

    expect(ask).toHaveBeenCalled()
  })

  it('says it is finding subjects while it waits', () => {
    render(<SubjectSuggestions {...base} phase="waiting" />)

    expect(screen.getByText('Finding subjects…')).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveAttribute('aria-busy', 'true')
  })

  it('lists each subject as a button that uses it', () => {
    const onChoose = vi.fn()
    render(<SubjectSuggestions {...base} phase="shown" subjects={['why cats purr', 'why we hiccup']} onChoose={onChoose} />)

    fireEvent.click(screen.getByRole('button', { name: 'Use: why cats purr' }))

    expect(screen.getAllByRole('listitem')).toHaveLength(2)
    expect(onChoose).toHaveBeenCalledWith('why cats purr')
  })

  it('says so when nothing new came back, or shows the provider’s message', () => {
    const { rerender } = render(<SubjectSuggestions {...base} phase="empty" />)
    expect(screen.getByText('No new subjects came back. Type one, or start without one.')).toBeInTheDocument()

    rerender(<SubjectSuggestions {...base} phase="error" message="Ollama isn't running." />)
    expect(screen.getByText("Ollama isn't running.")).toBeInTheDocument()
  })
})
