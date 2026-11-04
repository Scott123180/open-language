import { describe, it, expect } from 'vitest'
import { episodeReducer, initialEpisodeState } from './episodeState'
import type { EpisodeLine } from '../../services/podcastsApi'

const started = { event: 'line_started' as const, stream_id: 's1', host_id: 11 }
const part = (index: number, text: string) => ({
  event: 'line_part' as const,
  stream_id: 's1',
  index,
  text,
  audio_url: `/api/podcasts/episodes/57/parts/s1/${index}`,
})
const stored: EpisodeLine = {
  message_id: 101,
  speaker: 'host',
  host_id: 11,
  content: 'Hola a todos. Hoy hablamos de pan.',
  intent: 'react',
  invites_learner: false,
  is_revealed: false,
  created_at: '2026-11-03T10:00:00Z',
}

const arriving = () => {
  const begun = episodeReducer(initialEpisodeState, { type: 'lineStarted', event: started })
  const first = episodeReducer(begun, { type: 'linePart', event: part(0, 'Hola a todos.') })
  return episodeReducer(first, { type: 'linePart', event: part(1, 'Hoy hablamos de pan.') })
}

describe('a streamed line in the episode state (011 research R13)', () => {
  it('starts an arriving line for its host', () => {
    const state = episodeReducer(initialEpisodeState, { type: 'lineStarted', event: started })

    expect(state.arriving).toEqual({ streamId: 's1', hostId: 11, parts: [] })
  })

  it('adds each part as it comes', () => {
    expect(arriving().arriving?.parts.map((p) => p.text)).toEqual(['Hola a todos.', 'Hoy hablamos de pan.'])
  })

  it('replaces the arriving line with the stored line and remembers it was streamed', () => {
    const state = episodeReducer(arriving(), { type: 'line', frame: { event: 'line', line: stored, turn: 'hosts', awaiting: 'continue' } })

    expect(state.arriving).toBeNull()
    expect(state.lines).toEqual([stored])
    expect(state.streamedIds).toEqual([101])
    expect(state.streamParts?.parts).toHaveLength(2)
  })

  it('drops a lost line and says so', () => {
    const state = episodeReducer(arriving(), { type: 'lineLost', streamId: 's1' })

    expect(state.arriving).toBeNull()
    expect(state.lostStreamId).toBe('s1')
    expect(state.lines).toEqual([])
  })

  it('ignores a part of another stream', () => {
    const other = { ...part(0, 'Otra.'), stream_id: 's9' }

    expect(episodeReducer(arriving(), { type: 'linePart', event: other }).arriving?.parts).toHaveLength(2)
  })
})
