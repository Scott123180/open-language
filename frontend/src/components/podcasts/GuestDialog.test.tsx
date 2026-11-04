import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import GuestDialog from './GuestDialog'
import { hugo, ines } from './fixtures.test.utils'
import { catalog } from '../../pages/podcastPageFixtures.test.utils'

function renderDialog(onInvite = vi.fn(), onCancel = vi.fn()) {
  render(<GuestDialog host={ines} otherHost={hugo} personalities={catalog.personalities} onInvite={onInvite} onCancel={onCancel} />)
  return { onInvite, onCancel }
}

describe('GuestDialog (011 FR-020)', () => {
  it('asks for the guest’s personality in a radio group, without the other host’s', () => {
    renderDialog()

    const group = screen.getByRole('radiogroup', { name: "The guest's personality" })
    expect(group).toBeInTheDocument()
    expect(screen.queryByRole('radio', { name: /Curious interviewer/ })).not.toBeInTheDocument()
    expect(screen.getByRole('alertdialog', { name: 'Invite a guest in place of Inés?' })).toBeInTheDocument()
  })

  it('invites with the chosen personality', async () => {
    const { onInvite } = renderDialog()

    await userEvent.click(screen.getAllByRole('radio')[1])
    await userEvent.click(screen.getByRole('button', { name: 'Invite' }))

    expect(onInvite).toHaveBeenCalledWith(expect.any(String))
  })

  it('invites with any personality by default', async () => {
    const { onInvite } = renderDialog()

    await userEvent.click(screen.getByRole('button', { name: 'Invite' }))

    expect(onInvite).toHaveBeenCalledWith(null)
  })

  it('keeps focus inside and closes on Escape', async () => {
    const { onCancel } = renderDialog()

    await userEvent.tab()
    expect(screen.getByRole('alertdialog')).toContainElement(document.activeElement as HTMLElement)
    await userEvent.keyboard('{Escape}')

    expect(onCancel).toHaveBeenCalledOnce()
  })
})
