import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import SeriesHostCard from './SeriesHostCard'
import { hugo, ines } from './fixtures.test.utils'

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

describe('SeriesHostCard, a host who joins (011 R12)', () => {
  it('reads “New to the show” until the host has been in an episode', () => {
    render(<SeriesHostCard host={{ ...ines, has_taken_part: false }} onPlaySample={() => undefined} />)

    expect(screen.getByText('New to the show')).toBeInTheDocument()
  })

  it('says nothing for a host who has taken part', () => {
    render(<SeriesHostCard host={{ ...ines, has_taken_part: true }} onPlaySample={() => undefined} />)

    expect(screen.queryByText('New to the show')).not.toBeInTheDocument()
  })
})

describe('SeriesHostCard, inviting a guest (011 US4)', () => {
  it('offers Invite a guest… beside Recast…', () => {
    const onInvite = vi.fn()
    render(<SeriesHostCard host={hugo} onPlaySample={() => undefined} onRecast={() => undefined} onInvite={onInvite} />)

    fireEvent.click(screen.getByRole('button', { name: 'Invite a guest in place of Hugo' }))

    expect(screen.getByRole('button', { name: 'Recast Hugo' })).toBeInTheDocument()
    expect(onInvite).toHaveBeenCalledOnce()
  })

  it('reads “Away this episode” while a guest has the chair, with no actions', () => {
    render(<SeriesHostCard host={hugo} onPlaySample={() => undefined} onRecast={() => undefined} onInvite={() => undefined} isAway />)

    expect(screen.getByText('Away this episode')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Invite a guest/ })).not.toBeInTheDocument()
  })
})
