import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import GuestCard from './GuestCard'
import type { HostDraft } from '../../services/podcastsApi'

const marco: HostDraft = { slot: 'second', name: 'Marco', personality_id: 'expert', voice_key: 'es_AR-daniela-high', show_role: 'co_host', angle: null }

describe('GuestCard (011 contracts §11)', () => {
  it('reads as this episode’s guest with Another guest', async () => {
    const onAnother = vi.fn()
    render(<GuestCard guest={marco} personalityLabel="Expert" isCasting={false} error={null} onAnother={onAnother} />)

    expect(screen.getByText('Guest · this episode')).toBeInTheDocument()
    expect(screen.getByText('Marco')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Another guest' }))
    expect(onAnother).toHaveBeenCalledOnce()
  })

  it('says Casting… while the guest is cast', () => {
    render(<GuestCard guest={null} personalityLabel="" isCasting error={null} onAnother={vi.fn()} />)

    expect(screen.getByText('Casting…')).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveAttribute('aria-busy', 'true')
  })

  it('offers Remove guest only when the learner can remove them', async () => {
    const onRemove = vi.fn()
    render(<GuestCard guest={marco} personalityLabel="Expert" isCasting={false} error={null} onAnother={vi.fn()} onRemove={onRemove} />)

    await userEvent.click(screen.getByRole('button', { name: 'Remove guest' }))

    expect(onRemove).toHaveBeenCalledOnce()
  })

  it('shows why casting failed', () => {
    render(<GuestCard guest={null} personalityLabel="" isCasting={false} error="Ollama isn’t running." onAnother={vi.fn()} />)

    expect(screen.getByText('Ollama isn’t running.')).toBeInTheDocument()
  })
})
