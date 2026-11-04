import { act, renderHook } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { useEpisodeAudio } from './useEpisodeAudio'
import type { StreamedSpeech } from './useEpisodeAudio'
import type { EpisodeHost, EpisodeLine } from '../../services/podcastsApi'

vi.mock('../../services/api', () => ({ getTtsUrl: (id: number) => `/api/audio/tts/${id}` }))

const host = { host_id: 11, is_voice_available: true } as EpisodeHost
const line = (id: number): EpisodeLine => ({
  message_id: id,
  speaker: 'host',
  host_id: 11,
  content: 'Hola.',
  intent: 'react',
  invites_learner: false,
  is_revealed: false,
  created_at: '2026-11-03T10:00:00Z',
})
const part = (index: number) => ({
  event: 'line_part' as const,
  stream_id: 's1',
  index,
  text: `Frase ${index}.`,
  audio_url: `/parts/s1/${index}`,
})
const quiet: StreamedSpeech = { streamParts: null, streamedIds: [], lostStreamId: null }

describe('useEpisodeAudio with streamed lines', () => {
  it('plays a streamed line part by part', () => {
    const streamParts = { streamId: 's1', parts: [part(0), part(1)] }
    const { result } = renderHook(() => useEpisodeAudio([], [host], { ...quiet, streamParts }))

    expect(result.current.source?.src).toBe('/parts/s1/0')
    act(() => result.current.stopped())
    expect(result.current.source?.src).toBe('/parts/s1/1')
  })

  it('does not play a streamed line again when the line arrives', async () => {
    vi.useFakeTimers()
    const { result, rerender } = renderHook(({ lines, stream }) => useEpisodeAudio(lines, [host], stream), {
      initialProps: { lines: [] as EpisodeLine[], stream: quiet },
    })
    rerender({ lines: [line(101)], stream: { ...quiet, streamedIds: [101] } })
    await act(async () => vi.runAllTimers())

    expect(result.current.source).toBeNull()
    vi.useRealTimers()
  })

  it('stops a lost line\'s parts', () => {
    const streamParts = { streamId: 's1', parts: [part(0)] }
    const { result, rerender } = renderHook(({ stream }) => useEpisodeAudio([], [host], stream), {
      initialProps: { stream: { ...quiet, streamParts } as StreamedSpeech },
    })

    rerender({ stream: { ...quiet, lostStreamId: 's1' } })

    expect(result.current.source).toBeNull()
  })

  it('Replay stops the parts and plays the whole line', async () => {
    vi.useFakeTimers()
    const streamParts = { streamId: 's1', parts: [part(0)] }
    const { result } = renderHook(() => useEpisodeAudio([line(101)], [host], { ...quiet, streamParts }))

    act(() => result.current.play(101))
    await act(async () => vi.runAllTimers())

    expect(result.current.source?.src).toBe('/api/audio/tts/101')
    vi.useRealTimers()
  })
})

describe('parts that arrive with their line in one batch', () => {
  it('are still played', () => {
    const streamParts = { streamId: 's1', parts: [part(0)] }
    const { result } = renderHook(() => useEpisodeAudio([line(101)], [host], { streamParts, streamedIds: [101], lostStreamId: null }))

    expect(result.current.source?.src).toBe('/parts/s1/0')
  })
})
