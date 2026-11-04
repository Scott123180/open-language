import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import * as podcasts from '../../services/podcastsApi'
import type { HostDraft } from '../../services/podcastsApi'
import { useExpertGuest, useGuest } from './useGuest'

vi.mock('../../services/podcastsApi')

const marco: HostDraft = { slot: 'second', name: 'Marco', personality_id: 'expert', voice_key: 'es_AR-daniela-high', show_role: 'co_host', angle: null }
const sofia: HostDraft = { ...marco, name: 'Sofía' }

beforeEach(() => {
  vi.clearAllMocks()
})

describe('useGuest (011 R10)', () => {
  it('casts a guest for a seat and is casting until it arrives', async () => {
    let arrive: (guest: HostDraft) => void = () => undefined
    vi.mocked(podcasts.castGuest).mockReturnValue(new Promise((resolve) => (arrive = resolve)))
    const { result } = renderHook(() => useGuest(4, 'es', 'Sam'))

    act(() => void result.current.cast('second', 'panel', 'expert'))

    expect(result.current.isCasting).toBe(true)
    await act(async () => arrive(marco))
    expect(result.current.guest).toEqual(marco)
    expect(podcasts.castGuest).toHaveBeenCalledWith(4, {
      language: 'es', slot: 'second', format: 'panel', personality_id: 'expert', learner_name: 'Sam', avoid_names: [],
    })
  })

  it('Another guest re-casts the seat avoiding every name drawn so far', async () => {
    vi.mocked(podcasts.castGuest).mockResolvedValueOnce(marco).mockResolvedValueOnce(sofia)
    const { result } = renderHook(() => useGuest(4, 'es', ''))
    await act(() => result.current.cast('second', 'panel', 'expert'))

    await act(() => result.current.another())

    expect(vi.mocked(podcasts.castGuest).mock.calls[1][1]).toMatchObject({ personality_id: 'expert', avoid_names: ['Marco'], learner_name: null })
    expect(result.current.guest).toEqual(sofia)
  })

  it('removes the guest', async () => {
    vi.mocked(podcasts.castGuest).mockResolvedValue(marco)
    const { result } = renderHook(() => useGuest(4, 'es', ''))
    await act(() => result.current.cast('second', 'panel', 'expert'))

    act(() => result.current.remove())

    expect(result.current.guest).toBeNull()
  })

  it('keeps the server’s words when casting fails', async () => {
    vi.mocked(podcasts.castGuest).mockRejectedValue(new Error('That series isn’t there any more. Open the show again.'))
    const { result } = renderHook(() => useGuest(4, 'es', ''))

    await act(() => result.current.cast('second', 'panel', null))

    expect(result.current.error).toBe('That series isn’t there any more. Open the show again.')
    expect(result.current.isCasting).toBe(false)
  })
})

describe('useExpertGuest (011 FR-024a)', () => {
  it('casts the show’s expert when a One host series turns Panel for this episode', async () => {
    vi.mocked(podcasts.castGuest).mockResolvedValue(marco)
    const { result } = renderHook(({ isWanted }) => {
      const guest = useGuest(4, 'es', '')
      useExpertGuest(guest, { isWanted, format: 'panel', expertId: 'expert' })
      return guest
    }, { initialProps: { isWanted: true } })

    await waitFor(() => expect(result.current.guest).toEqual(marco))
    expect(podcasts.castGuest).toHaveBeenCalledOnce()
    expect(vi.mocked(podcasts.castGuest).mock.calls[0][1]).toMatchObject({ slot: 'second', personality_id: 'expert' })
  })

  it('removes the expert when the format goes back', async () => {
    vi.mocked(podcasts.castGuest).mockResolvedValue(marco)
    const { result, rerender } = renderHook(({ isWanted }) => {
      const guest = useGuest(4, 'es', '')
      useExpertGuest(guest, { isWanted, format: 'panel', expertId: 'expert' })
      return guest
    }, { initialProps: { isWanted: true } })
    await waitFor(() => expect(result.current.guest).toEqual(marco))

    rerender({ isWanted: false })

    expect(result.current.guest).toBeNull()
  })
})
