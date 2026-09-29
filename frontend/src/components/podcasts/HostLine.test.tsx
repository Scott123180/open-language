import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import HostLine from './HostLine'
import { hostLine, lucia } from './fixtures.test.utils'

vi.mock('../../services/api')

describe('HostLine', () => {
  it('shows the speaker name above the full line', () => {
    render(<HostLine line={hostLine} host={lucia} conversationId={57} />)

    expect(screen.getByText('Lucía')).toBeInTheDocument()
    expect(screen.getByText('¡Bienvenidos a Weekend Food Talk!')).toBeInTheDocument()
  })

  describe('hidden in Listen (FR-043)', () => {
    it('hides the words behind a button named for the speaker', () => {
      render(<HostLine line={hostLine} host={lucia} conversationId={57} isHidden onReveal={vi.fn()} />)

      expect(screen.queryByText('¡Bienvenidos a Weekend Food Talk!')).not.toBeInTheDocument()
      expect(screen.getByRole('button', { name: "Show Lucía's line" })).toBeInTheDocument()
    })

    it('reveals the words and reports it when tapped', () => {
      const onReveal = vi.fn()
      render(<HostLine line={hostLine} host={lucia} conversationId={57} isHidden onReveal={onReveal} />)

      fireEvent.click(screen.getByRole('button', { name: "Show Lucía's line" }))

      expect(onReveal).toHaveBeenCalledWith(901)
    })

    it('can be replayed while hidden', () => {
      const onReplay = vi.fn()
      render(<HostLine line={hostLine} host={lucia} conversationId={57} isHidden onReveal={vi.fn()} onReplay={onReplay} />)

      fireEvent.click(screen.getByRole('button', { name: "Replay Lucía's line" }))

      expect(onReplay).toHaveBeenCalled()
    })

    it('offers the learning tools only once revealed', () => {
      const { rerender } = render(<HostLine line={hostLine} host={lucia} conversationId={57} isHidden onReveal={vi.fn()} />)
      expect(screen.queryByRole('button', { name: /translat/i })).not.toBeInTheDocument()

      rerender(<HostLine line={hostLine} host={lucia} conversationId={57} isHidden={false} onReveal={vi.fn()} />)

      expect(screen.getByText('¡Bienvenidos a Weekend Food Talk!')).toBeInTheDocument()
    })
  })
})
