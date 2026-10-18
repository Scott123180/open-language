import { act, renderHook } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as podcasts from '../../services/podcastsApi'
import type { StartEpisodeBody } from '../../services/podcastsApi'
import { show } from '../../components/podcasts/fixtures.test.utils'
import { useStartEpisode } from './useStartEpisode'

vi.mock('../../services/podcastsApi')

const mockNavigate = vi.fn()
vi.mock('react-router-dom', () => ({ useNavigate: () => mockNavigate }))

const BODY: StartEpisodeBody = { show, format: 'panel', length: 'short', kind: 'series' }
const SERIES = { seriesId: 4, memoryStatus: 'pending' as const }

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(podcasts.startEpisode).mockResolvedValue({ conversation_id: 81 } as podcasts.Episode)
  vi.mocked(podcasts.catchUpSeriesMemory).mockResolvedValue({ status: 'up_to_date' })
})

describe('useStartEpisode', () => {
  it('starts at once when memory is up to date', async () => {
    const { result } = renderHook(() => useStartEpisode())

    await act(() => result.current.start(BODY, { seriesId: 4, memoryStatus: 'up_to_date' }))

    expect(podcasts.catchUpSeriesMemory).not.toHaveBeenCalled()
    expect(podcasts.startEpisode).toHaveBeenCalledWith(BODY)
    expect(mockNavigate).toHaveBeenCalledWith('/podcasts/episodes/81')
  })

  it('waits for the hosts to catch up, then starts', async () => {
    let finish: (value: podcasts.CatchUpResult) => void = () => undefined
    vi.mocked(podcasts.catchUpSeriesMemory).mockReturnValue(new Promise((resolve) => { finish = resolve }))
    const { result } = renderHook(() => useStartEpisode())

    let starting: Promise<void> = Promise.resolve()
    act(() => { starting = result.current.start(BODY, SERIES) })

    expect(result.current.catchUp.phase).toBe('catchingUp')
    expect(podcasts.catchUpSeriesMemory).toHaveBeenCalledWith(4, { wait: true })
    await act(async () => { finish({ status: 'up_to_date' }); await starting })
    expect(podcasts.startEpisode).toHaveBeenCalledWith(BODY)
  })

  it.each([
    ['failed', 'Ollama is not running.'],
    ['timed_out', "It's taking longer than usual."],
  ] as const)('offers a retry or a start without the update when the catch-up is %s', async (status, detail) => {
    vi.mocked(podcasts.catchUpSeriesMemory).mockResolvedValue({ status, detail })
    const { result } = renderHook(() => useStartEpisode())

    await act(() => result.current.start(BODY, SERIES))

    expect(result.current.catchUp).toEqual({ phase: status === 'failed' ? 'failed' : 'timedOut', detail })
    expect(podcasts.startEpisode).not.toHaveBeenCalled()
  })

  it('tries the catch-up again', async () => {
    vi.mocked(podcasts.catchUpSeriesMemory).mockResolvedValueOnce({ status: 'failed', detail: 'Down.' })
    const { result } = renderHook(() => useStartEpisode())
    await act(() => result.current.start(BODY, SERIES))

    await act(() => result.current.retry())

    expect(podcasts.catchUpSeriesMemory).toHaveBeenCalledTimes(2)
    expect(podcasts.startEpisode).toHaveBeenCalledWith(BODY)
  })

  it('starts without the update when the learner chooses to', async () => {
    vi.mocked(podcasts.catchUpSeriesMemory).mockResolvedValue({ status: 'failed', detail: 'Down.' })
    const { result } = renderHook(() => useStartEpisode())
    await act(() => result.current.start(BODY, SERIES))

    await act(() => result.current.startWithoutUpdate())

    expect(podcasts.startEpisode).toHaveBeenCalledWith(BODY)
    expect(podcasts.catchUpSeriesMemory).toHaveBeenCalledTimes(1)
  })

  it('shows a refused start in the server words', async () => {
    vi.mocked(podcasts.startEpisode).mockRejectedValue(new Error("This show's hosts changed. Open the show again."))
    const { result } = renderHook(() => useStartEpisode())

    await act(() => result.current.start(BODY))

    expect(result.current.error).toBe("This show's hosts changed. Open the show again.")
    expect(result.current.isStarting).toBe(false)
  })
})
