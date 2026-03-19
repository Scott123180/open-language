import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import ScenarioCard from './ScenarioCard'

describe('ScenarioCard', () => {
  const defaultProps = {
    title: 'Ordering Coffee',
    description: 'Practice ordering a coffee at a café.',
    onRefresh: vi.fn(),
    onStartChat: vi.fn(),
  }

  it('renders title from props', () => {
    render(<ScenarioCard {...defaultProps} />)
    expect(screen.getByText('Ordering Coffee')).toBeInTheDocument()
  })

  it('renders description from props', () => {
    render(<ScenarioCard {...defaultProps} />)
    expect(screen.getByText('Practice ordering a coffee at a café.')).toBeInTheDocument()
  })

  it('refresh button is present and triggers onRefresh when clicked', () => {
    const onRefresh = vi.fn()
    render(<ScenarioCard {...defaultProps} onRefresh={onRefresh} />)
    fireEvent.click(screen.getByRole('button', { name: /refresh/i }))
    expect(onRefresh).toHaveBeenCalledTimes(1)
  })

  it('"Start Chat" button triggers onStartChat when clicked', () => {
    const onStartChat = vi.fn()
    render(<ScenarioCard {...defaultProps} onStartChat={onStartChat} />)
    fireEvent.click(screen.getByRole('button', { name: /start chat/i }))
    expect(onStartChat).toHaveBeenCalledTimes(1)
  })

  it('disables buttons and shows loading indicator when isLoading=true', () => {
    render(<ScenarioCard {...defaultProps} isLoading={true} />)
    const refreshBtn = screen.getByRole('button', { name: /refresh/i })
    const startBtn = screen.getByRole('button', { name: /start chat/i })
    expect(refreshBtn).toBeDisabled()
    expect(startBtn).toBeDisabled()
    expect(screen.getByText('Loading…')).toBeInTheDocument()
  })
})
