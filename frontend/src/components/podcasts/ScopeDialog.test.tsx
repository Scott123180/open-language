import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import ScopeDialog from './ScopeDialog'

function renderDialog() {
  const handlers = { onAnswer: vi.fn(), onCancel: vi.fn() }
  render(
    <>
      <button type="button">Presented</button>
      <ScopeDialog setting="Style" {...handlers} />
    </>,
  )
  return handlers
}

describe('ScopeDialog (011 FR-016)', () => {
  it('asks which episodes the change is for, with the two answers', () => {
    renderDialog()

    expect(screen.getByRole('alertdialog', { name: 'Change for which episodes?' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Just this episode' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'This and later episodes' })).toBeInTheDocument()
  })

  it('names the setting being changed', () => {
    renderDialog()

    expect(screen.getByText(/Style/)).toBeInTheDocument()
  })

  it('answers this episode or later episodes', async () => {
    const { onAnswer } = renderDialog()

    await userEvent.click(screen.getByRole('button', { name: 'Just this episode' }))
    await userEvent.click(screen.getByRole('button', { name: 'This and later episodes' }))

    expect(onAnswer.mock.calls).toEqual([['this-episode'], ['from-now-on']])
  })

  it('reverts on Escape without answering', async () => {
    const { onAnswer, onCancel } = renderDialog()

    await userEvent.keyboard('{Escape}')

    expect(onCancel).toHaveBeenCalledOnce()
    expect(onAnswer).not.toHaveBeenCalled()
  })

  it('keeps focus inside the dialog', async () => {
    renderDialog()

    await userEvent.tab()
    await userEvent.tab()

    expect(screen.getByRole('alertdialog')).toContainElement(document.activeElement as HTMLElement)
  })

  it('gives focus back to the changed control when it closes', () => {
    const changed = document.createElement('button')
    document.body.appendChild(changed)
    changed.focus()
    const { unmount } = render(<ScopeDialog setting="Style" onAnswer={vi.fn()} onCancel={vi.fn()} />)

    unmount()

    expect(document.activeElement).toBe(changed)
  })
})
