import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import RecordButton from './RecordButton'

describe('RecordButton', () => {
  it('renders a microphone button in idle state', () => {
    render(
      <RecordButton
        isRecording={false}
        isProcessing={false}
        onStartRecording={vi.fn()}
        onStopRecording={vi.fn()}
      />,
    )
    expect(screen.getByRole('button', { name: 'Start recording' })).toBeInTheDocument()
  })

  it('calls onStartRecording when clicked in idle state', () => {
    const onStartRecording = vi.fn()
    render(
      <RecordButton
        isRecording={false}
        isProcessing={false}
        onStartRecording={onStartRecording}
        onStopRecording={vi.fn()}
      />,
    )
    fireEvent.click(screen.getByRole('button', { name: 'Start recording' }))
    expect(onStartRecording).toHaveBeenCalledTimes(1)
  })

  it('renders a stop button when isRecording=true', () => {
    render(
      <RecordButton
        isRecording={true}
        isProcessing={false}
        onStartRecording={vi.fn()}
        onStopRecording={vi.fn()}
      />,
    )
    expect(screen.getByRole('button', { name: 'Stop recording' })).toBeInTheDocument()
  })

  it('calls onStopRecording when clicked in recording state', () => {
    const onStopRecording = vi.fn()
    render(
      <RecordButton
        isRecording={true}
        isProcessing={false}
        onStartRecording={vi.fn()}
        onStopRecording={onStopRecording}
      />,
    )
    fireEvent.click(screen.getByRole('button', { name: 'Stop recording' }))
    expect(onStopRecording).toHaveBeenCalledTimes(1)
  })

  it('renders a disabled button with label "Processing…" when isProcessing=true', () => {
    render(
      <RecordButton
        isRecording={false}
        isProcessing={true}
        onStartRecording={vi.fn()}
        onStopRecording={vi.fn()}
      />,
    )
    const btn = screen.getByRole('button', { name: 'Processing…' })
    expect(btn).toBeDisabled()
  })
})
