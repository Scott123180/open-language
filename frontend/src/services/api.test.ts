import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import * as api from './api'

const BASE = '/api'

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

/** Serves `chunks` as an SSE body so the reader loop can be driven end to end. */
const stubSse = (chunks: string[], ok = true) => {
  const encoder = new TextEncoder()
  let i = 0
  const mock = vi.fn().mockResolvedValue({
    ok,
    status: ok ? 200 : 500,
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

const sse = (payload: unknown) => `data: ${JSON.stringify(payload)}\n`

beforeEach(() => {
  vi.clearAllMocks()
})
afterEach(() => {
  vi.unstubAllGlobals()
})

describe('apiFetch behaviour', () => {
  it('returns the parsed body with a JSON content type', async () => {
    const mock = stubJson([{ id: 1 }])

    await expect(api.getConversations()).resolves.toEqual([{ id: 1 }])
    expect(call(mock).init?.headers).toMatchObject({ 'Content-Type': 'application/json' })
  })

  it('throws the server detail on an error response', async () => {
    stubJson({ detail: 'Conversation not found' }, { ok: false, status: 404 })

    await expect(api.getConversation(1)).rejects.toThrow('Conversation not found')
  })

  it('falls back to the status code when the error body has no detail', async () => {
    stubJson({}, { ok: false, status: 503 })

    await expect(api.getConversations()).rejects.toThrow('HTTP 503')
  })

  it('falls back to the status code when the error body is not JSON', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error('not json')
        },
      })
    )

    await expect(api.getConversations()).rejects.toThrow('HTTP 500')
  })
})

describe('scenario and conversation endpoints', () => {
  it('gets the current scenario', async () => {
    const mock = stubJson({ id: 'a' })

    await api.getCurrentScenario()

    expect(call(mock).url).toBe(`${BASE}/scenarios/current`)
  })

  it('gets the next scenario with no exclusion', async () => {
    const mock = stubJson({ id: 'a' })

    await api.getNextScenario()

    expect(call(mock).url).toBe(`${BASE}/scenarios/next`)
  })

  it('url-encodes the excluded scenario id', async () => {
    const mock = stubJson({ id: 'a' })

    await api.getNextScenario('buy train/ticket')

    expect(call(mock).url).toBe(`${BASE}/scenarios/next?exclude_id=buy%20train%2Fticket`)
  })

  it('creates a conversation from a scenario id', async () => {
    const mock = stubJson({ id: 1 })

    await api.createConversation('order-coffee')

    expect(call(mock).body).toEqual({ scenario_id: 'order-coffee' })
  })

  it('creates a conversation from a custom prompt instead', async () => {
    const mock = stubJson({ id: 1 })

    await api.createConversation(null, 'Talk about hiking')

    expect(call(mock).body).toEqual({ custom_prompt: 'Talk about hiking' })
  })

  it('lists messages for a conversation', async () => {
    const mock = stubJson([])

    await api.getMessages(4)

    expect(call(mock).url).toBe(`${BASE}/conversations/4/messages`)
  })

  it('completes a conversation', async () => {
    const mock = stubJson({ id: 4 })

    await api.completeConversation(4)

    expect(call(mock).url).toBe(`${BASE}/conversations/4`)
  })
})

describe('audio endpoints', () => {
  it('posts the recording as multipart form data', async () => {
    const mock = stubJson({ text: 'hola' })

    await api.transcribeAudio(new Blob(['x']), 'Spanish')

    const { url, init } = call(mock)
    expect(url).toBe(`${BASE}/audio/transcribe`)
    expect(init?.body).toBeInstanceOf(FormData)
    expect((init?.body as FormData).get('language')).toBe('Spanish')
  })

  it('omits the language when none is given', async () => {
    const mock = stubJson({ text: 'hola' })

    await api.transcribeAudio(new Blob(['x']))

    expect((call(mock).init?.body as FormData).get('language')).toBeNull()
  })

  it('throws the transcription detail on failure', async () => {
    stubJson({ detail: 'Audio too short' }, { ok: false, status: 400 })

    await expect(api.transcribeAudio(new Blob(['x']))).rejects.toThrow('Audio too short')
  })

  it('falls back to the status code when the failure body is not JSON', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error('not json')
        },
      })
    )

    await expect(api.transcribeAudio(new Blob(['x']))).rejects.toThrow('HTTP 500')
  })

  it('builds a TTS url without calling the network', () => {
    const mock = stubJson({})

    expect(api.getTtsUrl(9)).toBe(`${BASE}/audio/tts/9`)
    expect(mock).not.toHaveBeenCalled()
  })
})

describe('streamChatOpen', () => {
  it('streams tokens and then the done payload', async () => {
    stubSse([sse({ token: 'Hola' }), sse({ token: ' amigo' }), sse({ done: true, message_id: 3 })])
    const onToken = vi.fn()
    const onDone = vi.fn()

    await api.streamChatOpen(1, onToken, onDone, vi.fn())

    expect(onToken.mock.calls.map(([t]) => t)).toEqual(['Hola', ' amigo'])
    expect(onDone).toHaveBeenCalledWith(expect.objectContaining({ message_id: 3 }))
  })

  it('reports a failed request without reading a stream', async () => {
    stubSse([], false)
    const onError = vi.fn()

    await api.streamChatOpen(1, vi.fn(), vi.fn(), onError)

    expect(onError).toHaveBeenCalledWith('HTTP 500')
  })

  it('reports a response with no body', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 200, body: null }))
    const onError = vi.fn()

    await api.streamChatOpen(1, vi.fn(), vi.fn(), onError)

    expect(onError).toHaveBeenCalledWith('No response body')
  })

  it('surfaces an error frame from the stream', async () => {
    stubSse([sse({ error: 'model unavailable' })])
    const onError = vi.fn()

    await api.streamChatOpen(1, vi.fn(), vi.fn(), onError)

    expect(onError).toHaveBeenCalledWith('model unavailable')
  })

  it('ignores the [DONE] sentinel and malformed frames', async () => {
    stubSse(['data: [DONE]\n', 'data: {not json}\n', 'noise\n', sse({ token: 'x' })])
    const onToken = vi.fn()
    const onError = vi.fn()

    await api.streamChatOpen(1, onToken, vi.fn(), onError)

    expect(onToken).toHaveBeenCalledOnce()
    expect(onToken).toHaveBeenCalledWith('x')
    expect(onError).not.toHaveBeenCalled()
  })

  it('reassembles a frame split across chunks', async () => {
    stubSse(['data: {"tok', 'en": "hi"}\n'])
    const onToken = vi.fn()

    await api.streamChatOpen(1, onToken, vi.fn(), vi.fn())

    expect(onToken).toHaveBeenCalledOnce()
    expect(onToken).toHaveBeenCalledWith('hi')
  })
})

describe('streamChatMessage', () => {
  const drive = async (chunks: string[], confidence?: number) => {
    const mock = stubSse(chunks)
    const cbs = {
      onUserSaved: vi.fn(),
      onToken: vi.fn(),
      onDone: vi.fn(),
      onError: vi.fn(),
      onFeedback: vi.fn(),
    }
    await api.streamChatMessage(
      1,
      'hola',
      'keyboard',
      cbs.onUserSaved,
      cbs.onToken,
      cbs.onDone,
      cbs.onError,
      cbs.onFeedback,
      confidence
    )
    return { mock, ...cbs }
  }

  it('sends the content and input source', async () => {
    const { mock } = await drive([])

    expect(call(mock).body).toEqual({ content: 'hola', input_source: 'keyboard' })
  })

  it('includes a zero confidence rather than dropping it as falsy', async () => {
    const { mock } = await drive([], 0)

    expect(call(mock).body).toMatchObject({ transcription_confidence: 0 })
  })

  it('includes an ordinary confidence', async () => {
    const { mock } = await drive([], 0.7)

    expect(call(mock).body).toMatchObject({ transcription_confidence: 0.7 })
  })

  it('omits the confidence when none is supplied', async () => {
    const { mock } = await drive([])

    expect(call(mock).body).not.toHaveProperty('transcription_confidence')
  })

  it('routes the user_message_saved event to its callback', async () => {
    const { onUserSaved } = await drive([sse({ event: 'user_message_saved', message_id: 11 })])

    expect(onUserSaved).toHaveBeenCalledOnce()
    expect(onUserSaved).toHaveBeenCalledWith(11)
  })

  it('routes the feedback event to its callback', async () => {
    const { onFeedback } = await drive([
      sse({ event: 'feedback', message_id: 11, awaiting_retry: true, notes: [] }),
    ])

    expect(onFeedback).toHaveBeenCalledWith(
      expect.objectContaining({ message_id: 11, awaiting_retry: true })
    )
  })

  it('passes a null message id through on a flagged turn', async () => {
    const { onDone } = await drive([sse({ done: true, message_id: null })])

    expect(onDone).toHaveBeenCalledWith(expect.objectContaining({ message_id: null }))
  })

  it('ignores an unknown event type', async () => {
    const { onUserSaved, onFeedback, onError } = await drive([sse({ event: 'something_else' })])

    expect(onUserSaved).not.toHaveBeenCalled()
    expect(onFeedback).not.toHaveBeenCalled()
    expect(onError).not.toHaveBeenCalled()
  })

  it('reports a failed request', async () => {
    stubSse([], false)
    const onError = vi.fn()

    await api.streamChatMessage(1, 'hola', 'keyboard', vi.fn(), vi.fn(), vi.fn(), onError)

    expect(onError).toHaveBeenCalledWith('HTTP 500')
  })

  it('tolerates a feedback event when no handler was supplied', async () => {
    stubSse([sse({ event: 'feedback', message_id: 11, awaiting_retry: false, notes: [] })])
    const onError = vi.fn()

    await api.streamChatMessage(1, 'hola', 'voice', vi.fn(), vi.fn(), vi.fn(), onError)

    expect(onError).not.toHaveBeenCalled()
  })
})

describe('streamHelper', () => {
  it('posts the helper session context and streams tokens', async () => {
    const mock = stubSse([sse({ token: 'try this' }), sse({ done: true })])
    const onToken = vi.fn()
    const onDone = vi.fn()

    await api.streamHelper('how do I say hi', 'sess-1', 'Spanish', 'English', onToken, onDone, vi.fn())

    expect(call(mock).body).toEqual({
      message: 'how do I say hi',
      helper_session_id: 'sess-1',
      target_language: 'Spanish',
      native_language: 'English',
    })
    expect(onToken).toHaveBeenCalledOnce()
    expect(onToken).toHaveBeenCalledWith('try this')
    expect(onDone).toHaveBeenCalledOnce()
  })

  it('reports a failed helper request', async () => {
    stubSse([], false)
    const onError = vi.fn()

    await api.streamHelper('x', 's', 'Spanish', 'English', vi.fn(), vi.fn(), onError)

    expect(onError).toHaveBeenCalledWith('HTTP 500')
  })
})

describe('learning tool endpoints', () => {
  it('checks grammar, nulling the preceding message when absent', async () => {
    const mock = stubJson({ result: 'ok', cached: false })

    await api.checkGrammar(1, 'hola')

    expect(call(mock).url).toBe(`${BASE}/learning/grammar`)
    expect(call(mock).body).toEqual({ message_id: 1, content: 'hola', preceding_message: null })
  })

  it('passes the preceding message when supplied', async () => {
    const mock = stubJson({ result: 'ok', cached: false })

    await api.checkGrammar(1, 'hola', '¿Qué tal?')

    expect(call(mock).body).toMatchObject({ preceding_message: '¿Qué tal?' })
  })

  it('translates a message', async () => {
    const mock = stubJson({ result: 'hello', cached: false })

    await api.translateMessage(1, 'hola', 'English')

    expect(call(mock).url).toBe(`${BASE}/learning/translate`)
    expect(call(mock).body).toEqual({ message_id: 1, content: 'hola', native_language: 'English' })
  })

  it('requests alternative phrasing', async () => {
    const mock = stubJson({ result: 'buenas', cached: false })

    await api.getAlternativePhrasing(1, 'hola', 'Spanish')

    expect(call(mock).url).toBe(`${BASE}/learning/phrasing`)
    expect(call(mock).body).toMatchObject({ target_language: 'Spanish' })
  })

  it('looks up a word, nulling the sentence context when absent', async () => {
    const mock = stubJson({ result: 'a greeting', cached: false })

    await api.lookupWord(1, 'hola', 'Spanish', 'English')

    expect(call(mock).url).toBe(`${BASE}/learning/word-lookup`)
    expect(call(mock).body).toMatchObject({ selection: 'hola', sentence_context: null })
  })

  it('passes the sentence context when supplied', async () => {
    const mock = stubJson({ result: 'a greeting', cached: false })

    await api.lookupWord(1, 'hola', 'Spanish', 'English', 'Hola, ¿qué tal?')

    expect(call(mock).body).toMatchObject({ sentence_context: 'Hola, ¿qué tal?' })
  })
})

describe('vocabulary, suggestions, settings and feedback', () => {
  it('saves a vocabulary item, nulling the source conversation when absent', async () => {
    const mock = stubJson({ id: 1 })

    await api.saveVocabularyItem('hola', 'hello')

    expect(call(mock).body).toEqual({
      word: 'hola',
      translation: 'hello',
      source_conversation_id: null,
    })
  })

  it('records the source conversation when supplied', async () => {
    const mock = stubJson({ id: 1 })

    await api.saveVocabularyItem('hola', 'hello', 4)

    expect(call(mock).body).toMatchObject({ source_conversation_id: 4 })
  })

  it('lists vocabulary', async () => {
    const mock = stubJson([])

    await api.getVocabulary()

    expect(call(mock).url).toBe(`${BASE}/vocabulary`)
  })

  it('fetches suggestions for a conversation', async () => {
    const mock = stubJson({ suggestions: [] })

    await api.getSuggestions(4)

    expect(call(mock).url).toContain('/chat/4')
  })

  it('gets settings', async () => {
    const mock = stubJson({ correction_mode: 'off' })

    await api.getSettings()

    expect(call(mock).url).toBe(`${BASE}/settings`)
  })

  it('updates settings with a PUT', async () => {
    const mock = stubJson({ correction_mode: 'strict' })

    await api.updateSettings({ correction_mode: 'strict' })

    expect(call(mock).init?.method).toBe('PUT')
    expect(call(mock).body).toEqual({ correction_mode: 'strict' })
  })

  it('lists voices', async () => {
    const mock = stubJson([])

    await api.getVoices()

    expect(call(mock).url).toBe(`${BASE}/settings/voices`)
  })

  it('fetches conversation feedback from the corrections module', async () => {
    const mock = stubJson({ conversation_id: 4, feedback: [] })

    await api.getConversationFeedback(4)

    expect(call(mock).url).toBe(`${BASE}/corrections/conversations/4`)
  })
})

describe('warmSession', () => {
  it('POSTs the conversation session endpoint', async () => {
    const mock = stubJson({ status: 'warming' }, { status: 202 })

    await api.warmSession(7)

    const { url, init } = call(mock)
    expect(url).toBe(`${BASE}/chat/7/session`)
    expect(init?.method).toBe('POST')
  })

  it.each([
    [202, true],
    [404, false],
    [409, false],
  ])('resolves quietly on HTTP %i', async (status, ok) => {
    stubJson({ detail: 'ignored' }, { ok, status })

    await expect(api.warmSession(7)).resolves.toBeUndefined()
  })

  it('resolves quietly when the network fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    await expect(api.warmSession(7)).resolves.toBeUndefined()
  })
})

describe('LLM provider selection', () => {
  const providers: api.LlmProviderOption[] = [
    {
      provider_id: 'ollama',
      display_name: 'Ollama (local)',
      is_local: true,
      models: [{ model_id: 'llama3.1:8b', label: 'llama3.1:8b' }],
      default_model: 'llama3.1:8b',
      effort_levels: [],
      default_effort: null,
      privacy_notice: null,
      is_available: true,
      unavailable_reason: null,
      unavailable_message: null,
    },
  ]

  it('getLlmProviders reads the provider catalogue', async () => {
    const mock = stubJson(providers)

    await expect(api.getLlmProviders()).resolves.toEqual(providers)
    expect(call(mock).url).toBe(`${BASE}/settings/llm-providers`)
  })

  it('updateSettings sends the provider, model, and effort', async () => {
    const mock = stubJson({})
    const update: Partial<api.AppSettings> = {
      llm_provider: 'claude',
      llm_model: 'sonnet',
      llm_effort: 'medium',
    }

    await api.updateSettings(update)

    expect(call(mock).body).toEqual(update)
  })

  it('a rejected save throws the server detail', async () => {
    stubJson(
      { detail: "That model isn't a Claude model. Choose Sonnet, Haiku, or Opus." },
      { ok: false, status: 422 },
    )

    await expect(api.updateSettings({ llm_provider: 'claude' })).rejects.toThrow(
      "That model isn't a Claude model. Choose Sonnet, Haiku, or Opus.",
    )
  })
})

describe('conversation levels (005)', () => {
  const levels: api.ConversationLevelOption[] = [
    {
      level_id: 'beginner',
      label: 'Beginner',
      cefr_label: 'A1',
      description: 'Very short, simple sentences — like talking with a young child.',
    },
    {
      level_id: 'natural',
      label: 'Natural',
      cefr_label: 'No limit',
      description: 'Ordinary everyday native speech, with no limits.',
    },
  ]

  it('getConversationLevels reads the level catalogue', async () => {
    const mock = stubJson(levels)

    await expect(api.getConversationLevels()).resolves.toEqual(levels)
    expect(call(mock).url).toBe(`${BASE}/settings/conversation-levels`)
    expect(call(mock).init?.method).toBeUndefined()
  })
})
