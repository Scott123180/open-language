import { renderHook, waitFor, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as podcasts from '../../services/podcastsApi'
import type { Episode, EpisodeLine, EpisodeStreamHandlers } from '../../services/podcastsApi'
import { usePodcastEpisode } from './usePodcastEpisode'

vi.mock('../../services/podcastsApi')

const hostLine = (id: number, invites = true): EpisodeLine => ({
  message_id: id,
  speaker: 'host',
  host_id: 11,
  content: `Línea ${id}`,
  intent: 'discuss',
  invites_learner: invites,
  is_revealed: false,
  created_at: '2026-09-28T10:00:00Z',
})

const episode = (overrides: Partial<Episode> = {}): Episode =>
  ({
    conversation_id: 57,
    status: 'active',
    format: 'one_host',
    hosts: [],
    lines: [],
    turn: 'hosts',
    awaiting: 'opening',
    can_jump_in: false,
    can_pass: false,
    ...overrides,
  }) as Episode

/** Makes a stream mock that answers with one host line and a done frame. */
const answersWith = (line: EpisodeLine, turn: 'hosts' | 'learner' | 'finished', awaiting: string | null = null) =>
  async (_id: number, ...rest: unknown[]) => {
    const handlers = rest[rest.length - 1] as EpisodeStreamHandlers
    handlers.onLine({ event: 'line', line, turn, awaiting: awaiting as never })
    handlers.onDone({ done: true, turn, awaiting: awaiting as never })
  }

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(podcasts.warmEpisodeSession).mockResolvedValue(undefined)
})

describe('usePodcastEpisode', () => {
  it('loads the episode', async () => {
    vi.mocked(podcasts.getEpisode).mockResolvedValue(episode({ turn: 'learner', awaiting: null, lines: [hostLine(1)] }))

    const { result } = renderHook(() => usePodcastEpisode(57))

    await waitFor(() => expect(result.current.episode?.conversation_id).toBe(57))
    expect(result.current.lines).toHaveLength(1)
    expect(result.current.turn).toBe('learner')
  })

  it('asks for the opening line by itself', async () => {
    vi.mocked(podcasts.getEpisode).mockResolvedValue(episode())
    vi.mocked(podcasts.streamEpisodeNext).mockImplementation(answersWith(hostLine(1), 'learner'))

    const { result } = renderHook(() => usePodcastEpisode(57))

    await waitFor(() => expect(result.current.lines).toHaveLength(1))
    expect(podcasts.streamEpisodeNext).toHaveBeenCalledTimes(1)
    expect(result.current.turn).toBe('learner')
  })

  it('asks for the reply to a learner line by itself', async () => {
    const learner = { ...hostLine(2), speaker: 'learner', host_id: null } as EpisodeLine
    vi.mocked(podcasts.getEpisode).mockResolvedValue(episode({ awaiting: 'reply', lines: [hostLine(1), learner] }))
    vi.mocked(podcasts.streamEpisodeNext).mockImplementation(answersWith(hostLine(3), 'learner'))

    renderHook(() => usePodcastEpisode(57))

    await waitFor(() => expect(podcasts.streamEpisodeNext).toHaveBeenCalledTimes(1))
  })

  it('waits for Continue', async () => {
    vi.mocked(podcasts.getEpisode).mockResolvedValue(episode({ awaiting: 'continue', lines: [hostLine(1, false)] }))

    const { result } = renderHook(() => usePodcastEpisode(57))

    await waitFor(() => expect(result.current.awaiting).toBe('continue'))
    expect(podcasts.streamEpisodeNext).not.toHaveBeenCalled()
  })

  it('appends the learner line then the host line after a reply', async () => {
    vi.mocked(podcasts.getEpisode).mockResolvedValue(episode({ turn: 'learner', awaiting: null, lines: [hostLine(1)] }))
    vi.mocked(podcasts.streamEpisodeMessage).mockImplementation(async (_id, _body, handlers) => {
      handlers.onUserSaved?.(2)
      handlers.onLine({ event: 'line', line: hostLine(3), turn: 'learner', awaiting: null })
      handlers.onDone({ done: true, turn: 'learner', awaiting: null })
    })
    const { result } = renderHook(() => usePodcastEpisode(57))
    await waitFor(() => expect(result.current.episode).not.toBeNull())

    await act(async () => result.current.send('Hola', 'keyboard'))

    expect(result.current.lines.map((l) => [l.message_id, l.speaker, l.content])).toEqual([
      [1, 'host', 'Línea 1'],
      [2, 'learner', 'Hola'],
      [3, 'host', 'Línea 3'],
    ])
  })

  it('ends the episode with the sign-off', async () => {
    vi.mocked(podcasts.getEpisode).mockResolvedValue(episode({ turn: 'learner', awaiting: null, lines: [hostLine(1)] }))
    vi.mocked(podcasts.streamEpisodeEnd).mockImplementation(answersWith({ ...hostLine(2, false), intent: 'sign_off' }, 'finished'))
    const { result } = renderHook(() => usePodcastEpisode(57))
    await waitFor(() => expect(result.current.episode).not.toBeNull())

    await act(async () => result.current.end())

    expect(result.current.turn).toBe('finished')
    expect(result.current.lines[result.current.lines.length - 1]?.intent).toBe('sign_off')
  })

  it('exposes an error and retries the line', async () => {
    vi.mocked(podcasts.getEpisode).mockResolvedValue(episode())
    vi.mocked(podcasts.streamEpisodeNext)
      .mockImplementationOnce(async (_id, handlers) => handlers.onError('The AI is not responding.'))
      .mockImplementationOnce(answersWith(hostLine(1), 'learner'))
    const { result } = renderHook(() => usePodcastEpisode(57))
    await waitFor(() => expect(result.current.error).toBe('The AI is not responding.'))

    await act(async () => result.current.retry())

    expect(result.current.error).toBeNull()
    expect(result.current.lines).toHaveLength(1)
  })

  it('ignores a second action while one is pending', async () => {
    vi.mocked(podcasts.getEpisode).mockResolvedValue(episode({ awaiting: 'continue', lines: [hostLine(1, false)] }))
    vi.mocked(podcasts.streamEpisodeNext).mockReturnValue(new Promise(() => {}))
    const { result } = renderHook(() => usePodcastEpisode(57))
    await waitFor(() => expect(result.current.episode).not.toBeNull())

    act(() => {
      result.current.next()
      result.current.next()
    })

    expect(podcasts.streamEpisodeNext).toHaveBeenCalledTimes(1)
    expect(result.current.isPending).toBe(true)
  })

  it('shows a load failure', async () => {
    vi.mocked(podcasts.getEpisode).mockRejectedValue(new Error('Episode not found'))

    const { result } = renderHook(() => usePodcastEpisode(57))

    await waitFor(() => expect(result.current.error).toBe('Episode not found'))
  })

  it('keeps feedback notes by message', async () => {
    vi.mocked(podcasts.getEpisode).mockResolvedValue(episode({ turn: 'learner', awaiting: null, lines: [hostLine(1)] }))
    vi.mocked(podcasts.streamEpisodeMessage).mockImplementation(async (_id, _body, handlers) => {
      handlers.onUserSaved?.(2)
      handlers.onFeedback?.({ message_id: 2, awaiting_retry: true, notes: [{ id: 5 } as never] })
      handlers.onDone({ done: true, turn: 'learner', awaiting: null })
    })
    const { result } = renderHook(() => usePodcastEpisode(57))
    await waitFor(() => expect(result.current.episode).not.toBeNull())

    await act(async () => result.current.send('Yo tener', 'keyboard'))

    expect(result.current.notes[2]).toHaveLength(1)
    expect(result.current.isAwaitingRetry).toBe(true)
  })

  it('reveals a hidden Listen line and tells the server', async () => {
    vi.mocked(podcasts.getEpisode).mockResolvedValue(episode({ format: 'listen', awaiting: 'continue', lines: [hostLine(1, false)] }))
    vi.mocked(podcasts.revealLine).mockResolvedValue(undefined)
    const { result } = renderHook(() => usePodcastEpisode(57))
    await waitFor(() => expect(result.current.episode).not.toBeNull())

    act(() => result.current.reveal(1))

    expect(result.current.lines[0].is_revealed).toBe(true)
    expect(podcasts.revealLine).toHaveBeenCalledWith(57, 1)
  })

  it('never lets the learner speak in Listen', async () => {
    vi.mocked(podcasts.getEpisode).mockResolvedValue(episode({ format: 'listen', awaiting: 'continue', lines: [hostLine(1, false)] }))

    const { result } = renderHook(() => usePodcastEpisode(57))

    await waitFor(() => expect(result.current.episode).not.toBeNull())
    expect(result.current.isListening).toBe(true)
  })

  it('jumps in without asking the server', async () => {
    vi.mocked(podcasts.getEpisode).mockResolvedValue(episode({ format: 'panel', awaiting: 'continue', can_jump_in: true, lines: [hostLine(1, false)] }))
    const { result } = renderHook(() => usePodcastEpisode(57))
    await waitFor(() => expect(result.current.canJumpIn).toBe(true))

    act(() => result.current.jumpIn())

    expect(result.current.isJumpingIn).toBe(true)
    expect(podcasts.streamEpisodeNext).not.toHaveBeenCalled()
  })

  it('passes by asking the hosts to carry on', async () => {
    vi.mocked(podcasts.getEpisode).mockResolvedValue(episode({ format: 'panel', turn: 'learner', awaiting: null, can_pass: true, lines: [hostLine(1)] }))
    vi.mocked(podcasts.streamEpisodePass).mockImplementation(answersWith(hostLine(2, false), 'hosts', 'continue'))
    const { result } = renderHook(() => usePodcastEpisode(57))
    await waitFor(() => expect(result.current.canPass).toBe(true))

    await act(async () => result.current.pass())

    expect(podcasts.streamEpisodePass).toHaveBeenCalledWith(57, expect.anything())
    expect(result.current.lines).toHaveLength(2)
  })
})
