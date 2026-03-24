import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import AudioControls from './AudioControls'

describe('AudioControls', () => {
  it('renders a Listen button', () => {
    render(<AudioControls ttsUrl="/api/flashcards/tts/1" />)
    expect(screen.getByRole('button', { name: /listen/i })).toBeInTheDocument()
  })

  it('renders a Slow Speed button', () => {
    render(<AudioControls ttsUrl="/api/flashcards/tts/1" />)
    expect(screen.getByRole('button', { name: /slow/i })).toBeInTheDocument()
  })

  it('calls onPlay at normal speed when Listen is clicked', () => {
    const onPlay = vi.fn()
    render(<AudioControls ttsUrl="/api/flashcards/tts/1" onPlay={onPlay} />)
    fireEvent.click(screen.getByRole('button', { name: /listen/i }))
    expect(onPlay).toHaveBeenCalledWith(1.0)
  })

  it('calls onPlay at slow speed (0.6) when Slow Speed is clicked', () => {
    const onPlay = vi.fn()
    render(<AudioControls ttsUrl="/api/flashcards/tts/1" onPlay={onPlay} />)
    fireEvent.click(screen.getByRole('button', { name: /slow/i }))
    expect(onPlay).toHaveBeenCalledWith(0.6)
  })
})
