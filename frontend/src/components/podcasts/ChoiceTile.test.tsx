import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import ChoiceTile from './ChoiceTile'

const option = { value: 'panel', label: 'Panel', detail: 'You and two hosts.' }

describe('ChoiceTile', () => {
  it('is a radio named by its label and detail', () => {
    render(<ChoiceTile group="podcast-format" option={option} isChecked onChoose={vi.fn()} />)

    expect(screen.getByRole('radio', { name: /Panel.*You and two hosts\./ })).toBeChecked()
  })

  it('reports a choice when clicked', () => {
    const onChoose = vi.fn()
    render(<ChoiceTile group="podcast-format" option={option} isChecked={false} onChoose={onChoose} />)

    fireEvent.click(screen.getByText('Panel'))

    expect(onChoose).toHaveBeenCalledOnce()
  })

  it('marks the checked tile with the primary selected state', () => {
    render(<ChoiceTile group="podcast-format" option={option} isChecked onChoose={vi.fn()} />)

    const tile = screen.getByRole('radio').closest('label') as HTMLElement
    expect(tile.style.background).toBe('var(--color-primary-subtle)')
    expect(tile.style.border).toContain('var(--color-primary)')
  })

  it('leaves an unchecked tile on the plain surface', () => {
    render(<ChoiceTile group="podcast-format" option={option} isChecked={false} onChoose={vi.fn()} />)

    const tile = screen.getByRole('radio').closest('label') as HTMLElement
    expect(tile.style.background).toBe('var(--color-surface)')
  })
})
