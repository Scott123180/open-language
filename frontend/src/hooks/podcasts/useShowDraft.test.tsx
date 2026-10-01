import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as podcasts from '../../services/podcastsApi'
import { generatedShow } from '../../components/podcasts/fixtures.test.utils'
import { useShowDraft } from './useShowDraft'

vi.mock('../../services/podcastsApi')

const secondVersion = { ...generatedShow, title: 'Far From Home' }

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(podcasts.generateShow).mockResolvedValue(generatedShow)
})

describe('useShowDraft', () => {
  it('generates a draft from the idea', async () => {
    const { result } = renderHook(() => useShowDraft())

    let made: Awaited<ReturnType<typeof result.current.generate>> = null
    await act(async () => { made = await result.current.generate('living abroad as a nurse') })

    expect(podcasts.generateShow).toHaveBeenCalledWith('living abroad as a nurse', [])
    expect(made).toEqual({ draft: generatedShow, idea: 'living abroad as a nurse', previousTitles: [] })
  })

  it('asks for a surprise', async () => {
    const surprise = { ...generatedShow, source: 'surprise' as const }
    vi.mocked(podcasts.surpriseShow).mockResolvedValue(surprise)
    const { result } = renderHook(() => useShowDraft())

    let made: Awaited<ReturnType<typeof result.current.surprise>> = null
    await act(async () => { made = await result.current.surprise() })

    expect(made).toEqual({ draft: surprise, idea: null, previousTitles: [] })
  })

  it('asks for another version avoiding every previous title', async () => {
    vi.mocked(podcasts.generateShow).mockResolvedValue(secondVersion)
    const { result } = renderHook(() => useShowDraft())
    const current = { draft: generatedShow, idea: 'nurses', previousTitles: ['Ward Stories'] }

    let made: Awaited<ReturnType<typeof result.current.anotherVersion>> = null
    await act(async () => { made = await result.current.anotherVersion(current) })

    expect(podcasts.generateShow).toHaveBeenCalledWith('nurses', ['Ward Stories', 'Night Shift Abroad'])
    expect(made).toEqual({ draft: secondVersion, idea: 'nurses', previousTitles: ['Ward Stories', 'Night Shift Abroad'] })
  })

  it('keeps the server’s plain words when a request is refused', async () => {
    vi.mocked(podcasts.generateShow).mockRejectedValue(new Error('Type a few words about the show you’d like, or press Surprise me.'))
    const { result } = renderHook(() => useShowDraft())

    let made: Awaited<ReturnType<typeof result.current.generate>> = null
    await act(async () => { made = await result.current.generate(' ') })

    expect(made).toBeNull()
    expect(result.current.error).toMatch(/Type a few words/)
    expect(result.current.isPending).toBe(false)
  })

  it('is pending while a show is on its way', async () => {
    let finish: (draft: typeof generatedShow) => void = () => {}
    vi.mocked(podcasts.generateShow).mockReturnValue(new Promise((resolve) => { finish = resolve }))
    const { result } = renderHook(() => useShowDraft())

    let request: Promise<unknown> = Promise.resolve()
    act(() => { request = result.current.generate('chess') })
    expect(result.current.isPending).toBe(true)

    await act(async () => { finish(generatedShow); await request })
    expect(result.current.isPending).toBe(false)
  })
})
