import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import RoleBadge from './RoleBadge'

describe('RoleBadge', () => {
  it.each([
    ['guest', "You're the guest"],
    ['co_host', "You're a co-host"],
    ['caller', "You're a caller"],
  ])('names the %s role', (role, text) => {
    render(<RoleBadge role={role} />)

    expect(screen.getByText(text)).toBeInTheDocument()
  })

  it('falls back to the raw role it does not know', () => {
    render(<RoleBadge role="judge" />)

    expect(screen.getByText('judge')).toBeInTheDocument()
  })

  it('gives each role its own icon', () => {
    const icons = ['guest', 'co_host', 'caller'].map((role) => {
      const { container, unmount } = render(<RoleBadge role={role} />)
      const icon = container.querySelector('svg')?.innerHTML
      unmount()
      return icon
    })

    expect(icons.every(Boolean)).toBe(true)
    expect(new Set(icons).size).toBe(3)
  })
})
