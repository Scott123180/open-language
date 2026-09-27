import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import * as api from './flashcardsApi'

const BASE = '/api/flashcards'

/** Stubs global fetch with one JSON response and returns the mock for assertions. */
const stubJson = (body: unknown, init: { ok?: boolean; status?: number } = {}) => {
  const mock = vi.fn().mockResolvedValue({
    ok: init.ok ?? true,
    status: init.status ?? 200,
    statusText: 'OK',
    json: async () => body,
  })
  vi.stubGlobal('fetch', mock)
  return mock
}

/** The (url, init) pair passed to fetch on its first call. */
const call = (mock: ReturnType<typeof vi.fn>) => {
  const [url, init] = mock.mock.calls[0] as [string, RequestInit | undefined]
  return { url, init, body: init?.body ? JSON.parse(init.body as string) : undefined }
}

beforeEach(() => {
  vi.clearAllMocks()
})
afterEach(() => {
  vi.unstubAllGlobals()
})

describe('apiFetch behaviour', () => {
  it('sends JSON content-type and returns the parsed body', async () => {
    const mock = stubJson([{ id: 1 }])

    await expect(api.listDecks('es')).resolves.toEqual([{ id: 1 }])
    expect(call(mock).init?.headers).toMatchObject({ 'Content-Type': 'application/json' })
  })

  it('resolves to undefined on 204 rather than parsing an empty body', async () => {
    stubJson(undefined, { status: 204 })

    await expect(api.deleteWord(3)).resolves.toBeUndefined()
  })

  it('throws the server detail message when the response is not ok', async () => {
    stubJson({ detail: 'Deck not found' }, { ok: false, status: 404 })

    await expect(api.getDeck(9)).rejects.toThrow('Deck not found')
  })

  it('falls back to the status text when the error body is not JSON', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => {
          throw new Error('not json')
        },
      })
    )

    await expect(api.listDecks('es')).rejects.toThrow('Internal Server Error')
  })
})

describe('word library endpoints', () => {
  it('requests only the language when no filters are given', async () => {
    const mock = stubJson([])

    await api.fetchWords('de')

    expect(call(mock).url).toBe(`${BASE}/words?language=de`)
  })

  it('repeats the classification parameter once per selected value', async () => {
    const mock = stubJson([])

    await api.fetchWords('es', { classification: ['difficult', 'learned'] })

    expect(call(mock).url).toBe(
      `${BASE}/words?language=es&classification=difficult&classification=learned`,
    )
  })

  it('passes date range and search filters through', async () => {
    const mock = stubJson([])

    await api.fetchWords('es', { date_from: '2026-01-01', date_to: '2026-02-01', search: 'hola' })

    const { url } = call(mock)
    expect(url).toContain('date_from=2026-01-01')
    expect(url).toContain('date_to=2026-02-01')
    expect(url).toContain('search=hola')
  })

  it('omits filters that are empty strings', async () => {
    const mock = stubJson([])

    await api.fetchWords('es', { search: '', date_from: '' })

    expect(call(mock).url).toBe(`${BASE}/words?language=es`)
  })

  it('PATCHes a single word classification', async () => {
    const mock = stubJson({ id: 4 })

    await api.updateClassification(4, 'almost_learned')

    const { url, init, body } = call(mock)
    expect(url).toBe(`${BASE}/words/4/classification`)
    expect(init?.method).toBe('PATCH')
    expect(body).toEqual({ classification: 'almost_learned' })
  })

  it('DELETEs a single word by id', async () => {
    const mock = stubJson(undefined, { status: 204 })

    await api.deleteWord(7)

    expect(call(mock).url).toBe(`${BASE}/words/7`)
    expect(call(mock).init?.method).toBe('DELETE')
  })

  it('DELETEs words in bulk with the ids in the body', async () => {
    const mock = stubJson({ deleted: 2 })

    await expect(api.deleteWords([1, 2])).resolves.toEqual({ deleted: 2 })
    expect(call(mock).body).toEqual({ ids: [1, 2] })
  })

  it('fetches cached word info by cache type', async () => {
    const mock = stubJson({ content: 'x', cached: true })

    await api.fetchWordInfo(5, 'phrases')

    expect(call(mock).url).toBe(`${BASE}/words/5/info/phrases`)
  })

  it('builds a vocabulary TTS url without calling the network', async () => {
    const mock = stubJson({})

    expect(api.getVocabTtsUrl(12)).toBe(`${BASE}/tts/12`)
    expect(mock).not.toHaveBeenCalled()
  })
})

describe('deck endpoints', () => {
  const payload: api.DeckConfigPayload = {
    language: 'de',
    size: 10,
    word_source: 'all',
    practice_mode: 'recall',
    algorithm: 'mixed_review',
  }

  it('POSTs a deck configuration', async () => {
    const mock = stubJson({ id: 1 })

    await api.createDeck(payload)

    const { url, init, body } = call(mock)
    expect(url).toBe(`${BASE}/decks`)
    expect(init?.method).toBe('POST')
    expect(body).toEqual(payload)
  })

  it('GETs a deck by id', async () => {
    const mock = stubJson({ id: 2 })

    await api.getDeck(2)

    expect(call(mock).url).toBe(`${BASE}/decks/2`)
  })

  it('PATCHes a deck name', async () => {
    const mock = stubJson({ id: 2 })

    await api.updateDeckName(2, 'Travel words')

    expect(call(mock).body).toEqual({ name: 'Travel words' })
    expect(call(mock).init?.method).toBe('PATCH')
  })

  it('POSTs a deck refresh', async () => {
    const mock = stubJson({ id: 2 })

    await api.refreshDeck(2)

    expect(call(mock).url).toBe(`${BASE}/decks/2/refresh`)
    expect(call(mock).init?.method).toBe('POST')
  })

  it('DELETEs a deck', async () => {
    const mock = stubJson(undefined, { status: 204 })

    await api.deleteDeck(3)

    expect(call(mock).url).toBe(`${BASE}/decks/3`)
    expect(call(mock).init?.method).toBe('DELETE')
  })
})

describe('session endpoints', () => {
  it('starts a session for a deck', async () => {
    const mock = stubJson({ id: 1 })

    await api.startSession(8)

    expect(call(mock).url).toBe(`${BASE}/sessions`)
    expect(call(mock).body).toEqual({ deck_id: 8 })
  })

  it('records a card result, nulling the optional fields when omitted', async () => {
    const mock = stubJson({ recorded: true })

    await api.recordCardResult(1, 0, 'knew_it')

    const { url, body } = call(mock)
    expect(url).toBe(`${BASE}/sessions/1/cards/0`)
    expect(body).toEqual({ rating: 'knew_it', response_type: null, user_response: null })
  })

  it('passes the response type and typed answer through when supplied', async () => {
    const mock = stubJson({ recorded: true })

    await api.recordCardResult(1, 2, 'guessed', 'typed', 'bonjour')

    expect(call(mock).body).toEqual({
      rating: 'guessed',
      response_type: 'typed',
      user_response: 'bonjour',
    })
  })

  it('ends a session with the completed flag', async () => {
    const mock = stubJson({ session_id: 1 })

    await api.endSession(1, true)

    expect(call(mock).url).toBe(`${BASE}/sessions/1/end`)
    expect(call(mock).body).toEqual({ completed: true })
  })

  it('fetches a session summary', async () => {
    const mock = stubJson({ session_id: 1 })

    await api.getSessionSummary(1)

    expect(call(mock).url).toBe(`${BASE}/sessions/1/summary`)
  })

  it('fetches the encouragement message', async () => {
    const mock = stubJson({ message: 'Nice work' })

    await expect(api.getEncouragement(1)).resolves.toEqual({ message: 'Nice work' })
    expect(call(mock).url).toBe(`${BASE}/sessions/1/encouragement`)
  })

  it('creates a deck from the missed cards', async () => {
    const mock = stubJson({ id: 4 })

    await api.createMissedDeck(1)

    expect(call(mock).url).toBe(`${BASE}/sessions/1/missed-deck`)
    expect(call(mock).init?.method).toBe('POST')
  })
})

describe('analytics endpoint', () => {
  it('defaults to the 7-day range', async () => {
    const mock = stubJson({})

    await api.fetchAnalytics('de')

    expect(call(mock).url).toBe(`${BASE}/analytics?language=de&range=7d`)
  })

  it('passes an explicit range through', async () => {
    const mock = stubJson({})

    await api.fetchAnalytics('es', 'all')

    expect(call(mock).url).toBe(`${BASE}/analytics?language=es&range=all`)
  })
})

describe('deck list and audio failures (006)', () => {
  it('lists one language\'s decks', async () => {
    const mock = stubJson([])

    await api.listDecks('de')

    expect(call(mock).url).toBe(`${BASE}/decks?language=de`)
  })

  it('a 503 explains why a word cannot be played', async () => {
    stubJson({ detail: "The German voice isn't installed." }, { ok: false, status: 503 })

    await expect(api.describeAudioFailure('/api/flashcards/tts/3')).resolves.toBe(
      "The German voice isn't installed.",
    )
  })

  it('any other failure gets a generic message', async () => {
    stubJson({ detail: 'boom' }, { ok: false, status: 500 })

    await expect(api.describeAudioFailure('/api/flashcards/tts/3')).resolves.toBe(
      'Audio is unavailable for this word.',
    )
  })

  it('a network error gets the generic message too', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))

    await expect(api.describeAudioFailure('/api/flashcards/tts/3')).resolves.toBe(
      'Audio is unavailable for this word.',
    )
  })
})
