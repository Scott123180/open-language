import { useState } from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import ConfirmDialog from './ConfirmDialog'

function Opener({ onConfirm = vi.fn(), onCancel = vi.fn() }) {
  const [isOpen, setOpen] = useState(false)
  const close = (callback: () => void) => () => {
    callback()
    setOpen(false)
  }
  return (
    <>
      <button type="button" onClick={() => setOpen(true)}>Start over…</button>
      {isOpen && (
        <ConfirmDialog title="Start over?" message="The hosts will forget this series." confirmLabel="Start over" isDestructive onConfirm={close(onConfirm)} onCancel={close(onCancel)}>
          <a href="#more">More</a>
        </ConfirmDialog>
      )}
    </>
  )
}

const open = async () => {
  await userEvent.click(screen.getByRole('button', { name: 'Start over…' }))
  return screen.getByRole('alertdialog')
}

describe('ConfirmDialog', () => {
  it('is an alert dialog named by its title and described by its message', async () => {
    render(<Opener />)

    const dialog = await open()

    expect(dialog).toHaveAccessibleName('Start over?')
    expect(dialog).toHaveAccessibleDescription('The hosts will forget this series.')
    expect(dialog).toHaveAttribute('aria-modal', 'true')
  })

  it('moves focus into the dialog and keeps it there', async () => {
    render(<Opener />)
    const dialog = await open()

    expect(dialog).toContainElement(document.activeElement as HTMLElement)
    for (let step = 0; step < 5; step += 1) {
      await userEvent.tab()
      expect(dialog).toContainElement(document.activeElement as HTMLElement)
    }
    await userEvent.tab({ shift: true })
    expect(dialog).toContainElement(document.activeElement as HTMLElement)
  })

  it.each([['Escape', '{Escape}'], ['Cancel', null]])('%s cancels and returns focus to the opener', async (_name, keys) => {
    const onCancel = vi.fn()
    render(<Opener onCancel={onCancel} />)
    await open()

    if (keys) await userEvent.keyboard(keys)
    else await userEvent.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(onCancel).toHaveBeenCalled()
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Start over…' })).toHaveFocus()
  })

  it('confirms', async () => {
    const onConfirm = vi.fn()
    render(<Opener onConfirm={onConfirm} />)
    await open()

    await userEvent.click(screen.getByRole('button', { name: 'Start over' }))

    expect(onConfirm).toHaveBeenCalled()
  })
})
