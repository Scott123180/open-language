import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import VoiceUnavailableNotice from './VoiceUnavailableNotice'

describe('VoiceUnavailableNotice', () => {
  it('announces the message as a status', () => {
    render(<VoiceUnavailableNotice message="The German voice isn't installed." />)

    expect(screen.getByRole('status')).toHaveTextContent("The German voice isn't installed.")
  })

  it('renders nothing without a message', () => {
    const { container } = render(<VoiceUnavailableNotice message={null} />)

    expect(container).toBeEmptyDOMElement()
  })
})
