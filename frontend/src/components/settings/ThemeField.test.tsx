import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, beforeEach } from 'vitest'
import ThemeField from './ThemeField'

beforeEach(() => {
  localStorage.clear()
  document.documentElement.removeAttribute('data-theme')
})

describe('ThemeField', () => {
  it('renders the Light, Dark and System buttons in a Theme group', () => {
    render(<ThemeField />)

    const group = screen.getByRole('group', { name: 'Theme' })
    expect(group).toContainElement(screen.getByRole('button', { name: 'Light' }))
    expect(screen.getByRole('button', { name: 'Dark' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'System' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('switches the theme when a button is pressed', () => {
    render(<ThemeField />)

    fireEvent.click(screen.getByRole('button', { name: 'Dark' }))

    expect(screen.getByRole('button', { name: 'Dark' })).toHaveAttribute('aria-pressed', 'true')
    expect(document.documentElement).toHaveAttribute('data-theme', 'dark')
  })
})
