import { useState } from 'react'
import { act, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import ThemedSelect, { type ThemedSelectOption } from './ThemedSelect'

const OPTIONS: ThemedSelectOption[] = [
  { value: 'enthusiast', label: 'Enthusiast' },
  { value: 'expert', label: 'Expert' },
  { value: 'contrarian', label: 'Contrarian' },
  { value: 'curious', label: 'Curious interviewer' },
]

function Controlled({ onChange = vi.fn(), disabled = false }: { onChange?: (v: string) => void; disabled?: boolean }) {
  const [value, setValue] = useState('expert')
  const choose = (next: string) => {
    setValue(next)
    onChange(next)
  }
  return (
    <>
      <ThemedSelect label="Personality" value={value} options={OPTIONS} onChange={choose} disabled={disabled} describedBy="hint" />
      <p id="hint">Pick one.</p>
      <button type="button">After</button>
    </>
  )
}

const trigger = () => screen.getByRole('combobox', { name: 'Personality' })
const activeOption = () => document.getElementById(trigger().getAttribute('aria-activedescendant') ?? '')

describe('ThemedSelect', () => {
  it('is a combobox named by its label, showing the chosen option', () => {
    render(<Controlled />)

    expect(trigger()).toHaveAttribute('aria-expanded', 'false')
    expect(trigger()).toHaveAttribute('aria-haspopup', 'listbox')
    expect(trigger()).toHaveTextContent('Expert')
    expect(trigger()).toHaveAttribute('aria-describedby', 'hint')
  })

  it('opens a listbox of options with the current one selected', async () => {
    render(<Controlled />)

    await userEvent.click(trigger())

    const listbox = screen.getByRole('listbox')
    expect(trigger()).toHaveAttribute('aria-expanded', 'true')
    expect(trigger()).toHaveAttribute('aria-controls', listbox.id)
    expect(screen.getAllByRole('option').map((o) => o.textContent)).toEqual(OPTIONS.map((o) => o.label))
    expect(screen.getByRole('option', { name: 'Expert' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('option', { name: 'Enthusiast' })).toHaveAttribute('aria-selected', 'false')
  })

  it.each(['{Enter}', ' ', '{Alt>}{ArrowDown}{/Alt}'])('opens with %s', async (keys) => {
    render(<Controlled />)
    trigger().focus()

    await userEvent.keyboard(keys)

    expect(screen.getByRole('listbox')).toBeInTheDocument()
    expect(activeOption()).toHaveTextContent('Expert')
  })

  it('moves the active option with the arrows, Home and End', async () => {
    render(<Controlled />)
    trigger().focus()
    await userEvent.keyboard('{Enter}')

    await userEvent.keyboard('{ArrowDown}')
    expect(activeOption()).toHaveTextContent('Contrarian')
    await userEvent.keyboard('{ArrowUp}{ArrowUp}')
    expect(activeOption()).toHaveTextContent('Enthusiast')
    await userEvent.keyboard('{End}')
    expect(activeOption()).toHaveTextContent('Curious interviewer')
    await userEvent.keyboard('{Home}')
    expect(activeOption()).toHaveTextContent('Enthusiast')
  })

  it('jumps to the next option starting with the typed letters', async () => {
    render(<Controlled />)
    trigger().focus()
    await userEvent.keyboard('{Enter}')

    await userEvent.keyboard('cu')

    expect(activeOption()).toHaveTextContent('Curious interviewer')
  })

  it('selects the active option with Enter and closes', async () => {
    const onChange = vi.fn()
    render(<Controlled onChange={onChange} />)
    trigger().focus()

    await userEvent.keyboard('{Enter}{ArrowDown}{Enter}')

    expect(onChange).toHaveBeenCalledWith('contrarian')
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
    expect(trigger()).toHaveTextContent('Contrarian')
    expect(trigger()).toHaveFocus()
  })

  it('closes with Escape without choosing', async () => {
    const onChange = vi.fn()
    render(<Controlled onChange={onChange} />)
    trigger().focus()

    await userEvent.keyboard('{Enter}{ArrowDown}{Escape}')

    expect(onChange).not.toHaveBeenCalled()
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
    expect(trigger()).toHaveTextContent('Expert')
  })

  it('selects the active option with Tab and moves focus on', async () => {
    const onChange = vi.fn()
    render(<Controlled onChange={onChange} />)
    trigger().focus()

    await userEvent.keyboard('{Enter}{ArrowUp}')
    await userEvent.tab()

    expect(onChange).toHaveBeenCalledWith('enthusiast')
    expect(screen.getByRole('button', { name: 'After' })).toHaveFocus()
  })

  it('selects a clicked option', async () => {
    const onChange = vi.fn()
    render(<Controlled onChange={onChange} />)

    await userEvent.click(trigger())
    await userEvent.click(screen.getByRole('option', { name: 'Contrarian' }))

    expect(onChange).toHaveBeenCalledWith('contrarian')
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
  })

  it('closes when focus leaves it', async () => {
    render(<Controlled />)
    await userEvent.click(trigger())

    await userEvent.click(screen.getByText('Pick one.'))

    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
  })

  it('marks the chosen option with a check and the active one with the focus outline', async () => {
    render(<Controlled />)
    trigger().focus()
    await userEvent.keyboard('{Enter}')

    const expert = screen.getByRole('option', { name: 'Expert' })
    expect(expert.querySelector('svg')).not.toBeNull()
    expect(expert).toHaveClass('themed-select-option--active')
    expect(screen.getByRole('option', { name: 'Contrarian' }).querySelector('svg')).toBeNull()

    act(() => {
      fireEvent.keyDown(trigger(), { key: 'ArrowDown' })
    })
    expect(expert).not.toHaveClass('themed-select-option--active')
    expect(screen.getByRole('option', { name: 'Contrarian' })).toHaveClass('themed-select-option--active')
  })

  it('cannot be opened while disabled', async () => {
    render(<Controlled disabled />)

    await userEvent.click(trigger())

    expect(trigger()).toBeDisabled()
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
  })
})
