import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import * as podcasts from './podcastsApi'

const BASE = '/api/podcasts'

const stubJson = (body: unknown, init: { ok?: boolean; status?: number } = {}) => {
  const mock = vi.fn().mockResolvedValue({
    ok: init.ok ?? true,
    status: init.status ?? 200,
    json: async () => body,
  })
  vi.stubGlobal('fetch', mock)
  return mock
}

const call = (mock: ReturnType<typeof vi.fn>) => {
  const [url, init] = mock.mock.calls[0] as [string, RequestInit | undefined]
  const raw = init?.body
  const body = typeof raw === 'string' ? JSON.parse(raw) : undefined
  return { url, init, body }
}

const stubSse = (chunks: string[], init: { ok?: boolean; status?: number; detail?: string } = {}) => {
  const encoder = new TextEncoder()
  let i = 0
  const mock = vi.fn().mockResolvedValue({
    ok: init.ok ?? true,
    status: init.status ?? 200,
    json: async () => ({ detail: init.detail }),
    body: {
      getReader: () => ({
        read: async () =>
          i < chunks.length
            ? { done: false, value: encoder.encode(chunks[i++]) }
            : { done: true, value: undefined },
      }),
    },
  })
  vi.stubGlobal('fetch', mock)
  return mock
}

const sse = (payload: unknown) => `data: ${JSON.stringify(payload)}\n\n`

const handlers = () => ({
  onLine: vi.fn(),
  onDone: vi.fn(),
  onError: vi.fn(),
  onUserSaved: vi.fn(),
  onFeedback: vi.fn(),
})

const line = { message_id: 7, speaker: 'host', host_id: 11, content: '¡Hola!' }

beforeEach(() => {
  vi.clearAllMocks()
})
afterEach(() => {
  vi.unstubAllGlobals()
})

describe('podcast JSON endpoints', () => {
  it('reads the catalogue', async () => {
    const mock = stubJson({ shows: [] })

    await expect(podcasts.getPodcastCatalog()).resolves.toEqual({ shows: [] })
    expect(call(mock).url).toBe(`${BASE}/catalog`)
  })

  it('reads and updates the preferences', async () => {
    const mock = stubJson({ learner_name: 'Sam' })

    await podcasts.updatePodcastPreferences({ learner_name: 'Sam' })

    expect(call(mock)).toMatchObject({ url: `${BASE}/preferences`, body: { learner_name: 'Sam' } })
    expect(call(mock).init?.method).toBe('PUT')
  })

  it('reads the preferences', async () => {
    const mock = stubJson({ last_format: 'panel' })

    await expect(podcasts.getPodcastPreferences()).resolves.toEqual({ last_format: 'panel' })
    expect(call(mock).url).toBe(`${BASE}/preferences`)
  })

  it('starts an episode with the draft, format and length', async () => {
    const mock = stubJson({ conversation_id: 57 })
    const body = { show: { title: 'T' }, format: 'panel', length: 'short' } as unknown as podcasts.StartEpisodeBody

    await expect(podcasts.startEpisode(body)).resolves.toEqual({ conversation_id: 57 })
    expect(call(mock)).toMatchObject({ url: `${BASE}/episodes`, body })
  })

  it('reads one episode and the list', async () => {
    const mock = stubJson([])

    await podcasts.listEpisodes()
    await podcasts.getEpisode(57)

    expect(mock.mock.calls.map((c) => c[0])).toEqual([`${BASE}/episodes`, `${BASE}/episodes/57`])
  })

  it('throws the server detail on an error', async () => {
    stubJson({ detail: 'Episode not found' }, { ok: false, status: 404 })

    await expect(podcasts.getEpisode(1)).rejects.toThrow('Episode not found')
  })

  it('reads a validation refusal as its plain sentences', async () => {
    stubJson({ detail: [{ msg: 'Value error, You can save at most 10 interests.' }] }, { ok: false, status: 422 })

    await expect(podcasts.updatePodcastPreferences({ interests: [] })).rejects.toThrow(/^You can save at most 10 interests\.$/)
  })

  it('generates a show from an idea, avoiding earlier titles', async () => {
    const mock = stubJson({ title: 'Night Shift Abroad' })

    await podcasts.generateShow('nurses', ['Ward Stories'])

    expect(call(mock)).toMatchObject({ url: `${BASE}/shows/generate`, body: { idea: 'nurses', avoid_titles: ['Ward Stories'] } })
  })

  it('throws a declined idea in its plain words', async () => {
    stubJson({ detail: "That idea can't become a show here.", can_surprise: true }, { ok: false, status: 422 })

    await expect(podcasts.generateShow('x')).rejects.toThrow("That idea can't become a show here.")
  })

  it('asks for a surprise', async () => {
    const mock = stubJson({ title: 'Chess Stories' })

    await podcasts.surpriseShow()

    expect(call(mock)).toMatchObject({ url: `${BASE}/shows/surprise`, body: {} })
  })

  it('shuffles a host', async () => {
    const mock = stubJson({ name: 'Pablo' })
    const body = { language: 'es', slot: 'second' as const, hosts: [], learner_name: null }

    await podcasts.shuffleHost(body)

    expect(call(mock)).toMatchObject({ url: `${BASE}/hosts/shuffle`, body })
  })

  it('builds a voice sample address with the name encoded', () => {
    expect(podcasts.voiceSampleUrl('es_AR-daniela-high', 'Lucía')).toBe(`${BASE}/voice-sample?voice_key=es_AR-daniela-high&name=Luc%C3%ADa`)
  })

  it('asks for suggestions for the episode', async () => {
    const mock = stubJson({ suggestions: ['Sí'] })

    await expect(podcasts.getEpisodeSuggestions(57)).resolves.toEqual({ suggestions: ['Sí'] })
    expect(call(mock).url).toBe(`${BASE}/episodes/57/suggestions`)
  })

  it('warms the session and ignores any failure', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))

    await expect(podcasts.warmEpisodeSession(57)).resolves.toBeUndefined()
  })
})

describe('podcast line streams', () => {
  it('parses a line then done for next', async () => {
    const mock = stubSse([sse({ event: 'line', line, turn: 'learner', awaiting: null }), sse({ done: true, turn: 'learner' })])
    const cbs = handlers()

    await podcasts.streamEpisodeNext(57, cbs)

    expect(call(mock).url).toBe(`${BASE}/episodes/57/next`)
    expect(cbs.onLine).toHaveBeenCalledWith({ event: 'line', line, turn: 'learner', awaiting: null })
    expect(cbs.onDone).toHaveBeenCalledWith({ done: true, turn: 'learner' })
  })

  it('sends the learner message and reports the saved id and feedback', async () => {
    const mock = stubSse([
      sse({ event: 'user_message_saved', message_id: 9 }),
      sse({ event: 'feedback', message_id: 9, awaiting_retry: true, notes: [] }),
      sse({ done: true, turn: 'learner' }),
    ])
    const cbs = handlers()

    await podcasts.streamEpisodeMessage(57, { content: 'hola', input_source: 'voice', transcription_confidence: 0 }, cbs)

    expect(call(mock).body).toEqual({ content: 'hola', input_source: 'voice', transcription_confidence: 0 })
    expect(cbs.onUserSaved).toHaveBeenCalledWith(9)
    expect(cbs.onFeedback).toHaveBeenCalledWith(expect.objectContaining({ awaiting_retry: true }))
  })

  it('ends the episode', async () => {
    const mock = stubSse([sse({ done: true, turn: 'finished' })])
    const cbs = handlers()

    await podcasts.streamEpisodeEnd(57, cbs)

    expect(call(mock).url).toBe(`${BASE}/episodes/57/end`)
    expect(cbs.onDone).toHaveBeenCalledWith({ done: true, turn: 'finished' })
  })

  it('reports an error frame', async () => {
    stubSse([sse({ error: 'The AI is not responding.' })])
    const cbs = handlers()

    await podcasts.streamEpisodeNext(57, cbs)

    expect(cbs.onError).toHaveBeenCalledWith('The AI is not responding.')
  })

  it('reports a refused action with its plain message', async () => {
    stubSse([], { ok: false, status: 409, detail: 'A line is already on its way.' })
    const cbs = handlers()

    await podcasts.streamEpisodeNext(57, cbs)

    expect(cbs.onError).toHaveBeenCalledWith('A line is already on its way.')
  })

  it('ignores a malformed frame', async () => {
    stubSse(['data: {not json\n\n', sse({ done: true, turn: 'hosts' })])
    const cbs = handlers()

    await podcasts.streamEpisodeNext(57, cbs)

    expect(cbs.onDone).toHaveBeenCalledTimes(1)
    expect(cbs.onError).not.toHaveBeenCalled()
  })
})
