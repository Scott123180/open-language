import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import SeriesHostCard from './SeriesHostCard'
import { hugo } from './fixtures.test.utils'

describe('SeriesHostCard', () => {
  it('shows the host read-only with a voice sample', () => {
    const onPlaySample = vi.fn()
    render(<SeriesHostCard host={hugo} onPlaySample={onPlaySample} />)

    expect(screen.getByText('Hugo')).toBeInTheDocument()
    expect(screen.getByText('Curious interviewer')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: "Play Hugo's voice" }))
    expect(onPlaySample).toHaveBeenCalled()
  })

  it('offers no Shuffle and no personality choice', () => {
    render(<SeriesHostCard host={hugo} onPlaySample={vi.fn()} />)

    expect(screen.queryByRole('button', { name: /Shuffle/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
  })

  it('keeps a host whose voice is missing, with the plain message and no sample', () => {
    const message = "Hugo's voice isn't installed, so Hugo's lines can't be read aloud."
    render(<SeriesHostCard host={{ ...hugo, is_voice_available: false, voice_unavailable_message: message }} onPlaySample={vi.fn()} />)

    expect(screen.getByText('Hugo')).toBeInTheDocument()
    expect(screen.getByText('Curious interviewer')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: "Play Hugo's voice" })).toBeDisabled()
    expect(screen.getByText(message)).toBeInTheDocument()
  })
})
