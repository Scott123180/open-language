import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import RecastDialog from './RecastDialog'
import { hugo, ines, personalities } from './fixtures.test.utils'

const expert = { personality_id: 'expert', label: 'Expert', description: 'Knows the facts.' }
const curious = { personality_id: 'curious_interviewer', label: 'Curious interviewer', description: 'Asks why.' }
const ALL = [...personalities, expert, curious]

const renderDialog = (overrides = {}) => {
  const props = { host: ines, otherHost: hugo, personalities: ALL, keepsVoice: false, isBusy: false, error: null, onConfirm: vi.fn(), onCancel: vi.fn(), ...overrides }
  render(<RecastDialog {...props} />)
  return props
}

describe('RecastDialog', () => {
  it('says the new host will not know the earlier history', () => {
    renderDialog()

    expect(screen.getByRole('alertdialog')).toHaveAccessibleDescription(/won't know what was said in earlier episodes/)
  })

  it('offers Any and every personality but the other host’s', async () => {
    renderDialog()

    await userEvent.click(screen.getByRole('combobox', { name: "The new host's personality" }))

    const options = screen.getAllByRole('option').map((option) => option.textContent)
    expect(options).toEqual(['Any', 'Enthusiast', 'Dry sceptic', 'Expert'])
  })

  it('notes when the new host keeps the voice', () => {
    renderDialog({ keepsVoice: true })

    expect(screen.getByText(/keeps this voice/)).toBeInTheDocument()
  })

  it('sends nothing on Cancel', async () => {
    const props = renderDialog()

    await userEvent.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(props.onCancel).toHaveBeenCalled()
    expect(props.onConfirm).not.toHaveBeenCalled()
  })

  it('confirms with the chosen personality, or none for Any', async () => {
    const props = renderDialog()

    await userEvent.click(screen.getByRole('button', { name: 'Recast' }))
    expect(props.onConfirm).toHaveBeenLastCalledWith(null)

    await userEvent.click(screen.getByRole('combobox', { name: "The new host's personality" }))
    await userEvent.click(screen.getByRole('option', { name: 'Expert' }))
    await userEvent.click(screen.getByRole('button', { name: 'Recast' }))
    expect(props.onConfirm).toHaveBeenLastCalledWith('expert')
  })
})
