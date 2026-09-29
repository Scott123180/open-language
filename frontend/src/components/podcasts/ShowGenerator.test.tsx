import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import ShowGenerator from './ShowGenerator'

const DECLINED = "That idea can't become a show here. Try a different topic, or press Surprise me."

const renderGenerator = (overrides: Partial<Parameters<typeof ShowGenerator>[0]> = {}) => {
  const props = { onGenerate: vi.fn(), onSurprise: vi.fn(), isPending: false, error: null, ...overrides }
  render(<ShowGenerator {...props} />)
  return props
}

describe('ShowGenerator', () => {
  it('has a labelled idea input, Generate and Surprise me', () => {
    renderGenerator()

    expect(screen.getByLabelText('Your show idea')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Generate' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Surprise me' })).toBeInTheDocument()
  })

  it('generates a show from the typed idea', () => {
    const props = renderGenerator()

    fireEvent.change(screen.getByLabelText('Your show idea'), { target: { value: 'football tactics' } })
    fireEvent.click(screen.getByRole('button', { name: 'Generate' }))

    expect(props.onGenerate).toHaveBeenCalledWith('football tactics')
  })

  it('generates on Enter in the idea input', () => {
    const props = renderGenerator()
    const input = screen.getByLabelText('Your show idea')

    fireEvent.change(input, { target: { value: 'night markets' } })
    fireEvent.submit(input)

    expect(props.onGenerate).toHaveBeenCalledWith('night markets')
  })

  it('asks for a surprise', () => {
    const props = renderGenerator()

    fireEvent.click(screen.getByRole('button', { name: 'Surprise me' }))

    expect(props.onSurprise).toHaveBeenCalled()
  })

  it('says a show is being created and disables both actions while pending', () => {
    renderGenerator({ isPending: true })

    expect(screen.getByRole('status')).toHaveTextContent('Creating your show…')
    expect(screen.getByRole('button', { name: 'Generate' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Surprise me' })).toBeDisabled()
  })

  it('shows a refusal as an alert and keeps Surprise me on offer', () => {
    renderGenerator({ error: DECLINED })

    expect(screen.getByRole('alert')).toHaveTextContent(DECLINED)
    expect(screen.getByRole('button', { name: 'Surprise me' })).toBeEnabled()
  })
})
