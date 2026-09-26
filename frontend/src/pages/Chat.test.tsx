import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import Chat from './Chat'
import * as api from '../services/api'

vi.mock('../services/api')

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => ({
  ...(await vi.importActual<typeof import('react-router-dom')>('react-router-dom')),
  useNavigate: () => mockNavigate,
}))

const mockStopRecording = vi.fn()
let isRecording = false
vi.mock('../hooks/useRecorder', () => ({
  useRecorder: () => ({
    startRecording: vi.fn(),
    stopRecording: mockStopRecording,
    isRecording,
    error: null,
  }),
}))

const CONV_ID = 7

const settings = (correction_mode: api.CorrectionMode): api.AppSettings => ({
  llm_provider: 'ollama',
  llm_model: 'llama3.1',
  llm_effort: 'low',
  target_language: 'Spanish',
  native_language: 'English',
  tts_voice: 'es_ES-sharvard-medium',
  suggestion_count: 3,
  whisper_model: 'small',
  correction_mode,
  updated_at: '2026-08-27T00:00:00Z',
})

const conversation: api.Conversation = {
  id: CONV_ID,
  scenario_id: 'order-coffee',
  scenario_title: 'Ordering Coffee',
  target_language: 'Spanish',
  native_language: 'English',
  status: 'active',
  started_at: '2026-08-27T00:00:00Z',
  ended_at: null,
  llm_model: 'llama3.1',
  custom_prompt: null,
}

const existingMessage: api.Message = {
  id: 10,
  conversation_id: CONV_ID,
  role: 'assistant',
  content: 'Hola, ¿qué desea?',
  input_source: null,
  created_at: '2026-08-27T00:00:00Z',
  tts_audio_path: null,
}

/** The flagged learner turn a resumed Strict pause leaves behind. */
const existingLearnerMessage: api.Message = {
  id: 11,
  conversation_id: CONV_ID,
  role: 'user',
  content: 'yo querer un cafe',
  input_source: 'keyboard',
  created_at: '2026-08-27T00:01:00Z',
  tts_audio_path: null,
}

const correctionNote: api.FeedbackNoteData = {
  id: 1,
  message_id: 11,
  kind: 'correction',
  category: 'verb_conjugation',
  error_fragment: 'yo querer',
  corrected_text: 'yo quiero',
  explanation: '"querer" needs conjugating to "quiero" in the first person.',
  mode: 'strict',
  rank: 0,
  created_at: '2026-08-27T00:00:00Z',
}

const emptyFeedback = (over: Partial<api.ConversationFeedback> = {}): api.ConversationFeedback => ({
  conversation_id: CONV_ID,
  awaiting_retry: false,
  awaiting_clarification: false,
  consecutive_corrected_attempts: 0,
  feedback: [],
  ...over,
})

const transcription = (confidence: number | null): api.TranscriptionResult => ({
  text: 'hola',
  detected_language: 'es',
  confidence,
  is_low_confidence: confidence != null && confidence < 0.55,
})

/** Captures streamChatMessage's callbacks so a test can drive the turn frame by frame. */
interface TurnDriver {
  userSaved: (id: number) => void
  token: (t: string) => void
  done: (messageId: number | null) => void
  feedback: (data: api.FeedbackEventData) => void
  confidenceArg: () => number | undefined
}

const captureTurn = (): TurnDriver => {
  let onUserSaved: ((id: number) => void) | undefined
  let onToken: ((t: string) => void) | undefined
  let onDone: ((d: { message_id: number | null }) => void) | undefined
  let onFeedback: ((d: api.FeedbackEventData) => void) | undefined
  let confidence: number | undefined

  vi.mocked(api.streamChatMessage).mockImplementation(
    async (_id, _content, _source, userSaved, token, done, _onError, feedback, sentConfidence) => {
      onUserSaved = userSaved
      onToken = token
      onDone = done
      onFeedback = feedback
      confidence = sentConfidence
    }
  )

  return {
    userSaved: (id) => act(() => onUserSaved?.(id)),
    token: (t) => act(() => onToken?.(t)),
    done: (messageId) => act(() => onDone?.({ message_id: messageId })),
    feedback: (data) => act(() => onFeedback?.(data)),
    confidenceArg: () => confidence,
  }
}

/** Captures streamChatOpen's callbacks so a test can drive the opening line. */
const captureOpening = () => {
  let onToken: ((t: string) => void) | undefined
  let onDone: ((d: { message_id: number }) => void) | undefined
  let onError: ((e: string) => void) | undefined

  vi.mocked(api.streamChatOpen).mockImplementation(async (_id, token, done, error) => {
    onToken = token
    onDone = done as (d: { message_id: number }) => void
    onError = error
  })

  return {
    token: (t: string) => act(() => onToken?.(t)),
    done: (messageId: number) => act(() => onDone?.({ message_id: messageId })),
    error: (message: string) => act(() => onError?.(message)),
  }
}

const renderChat = () =>
  render(
    <MemoryRouter initialEntries={[`/chat/${CONV_ID}`]}>
      <Routes>
        <Route path="/chat/:conversationId" element={<Chat />} />
      </Routes>
    </MemoryRouter>
  )

/** Renders a resumed conversation and waits for the composer to appear. */
const renderResumed = async () => {
  const view = renderChat()
  await screen.findByLabelText('Type a message')
  return view
}

const sendText = (text: string) => {
  fireEvent.change(screen.getByLabelText('Type a message'), { target: { value: text } })
  fireEvent.click(screen.getByLabelText('Send message'))
}

const composer = () => screen.getByLabelText('Type a message')

/**
 * useAudio drives a detached `new Audio()` and AudioPlayer renders null, so there
 * is no <audio> node to inspect. Record what actually reaches playback instead.
 */
const playedSources: string[] = []

beforeEach(() => {
  vi.clearAllMocks()
  playedSources.length = 0

  // jsdom implements none of these, and Chat reaches all three on a normal turn.
  Element.prototype.scrollIntoView = vi.fn()
  HTMLMediaElement.prototype.pause = vi.fn()
  HTMLMediaElement.prototype.play = vi.fn(function (this: HTMLMediaElement) {
    playedSources.push(this.src)
    return Promise.resolve()
  })

  isRecording = false
  vi.mocked(api.getSettings).mockResolvedValue(settings('off'))
  vi.mocked(api.getConversation).mockResolvedValue(conversation)
  vi.mocked(api.getMessages).mockResolvedValue([existingMessage])
  vi.mocked(api.getConversationFeedback).mockResolvedValue(emptyFeedback())
  vi.mocked(api.streamChatOpen).mockResolvedValue(undefined)
  vi.mocked(api.streamChatMessage).mockResolvedValue(undefined)
  vi.mocked(api.transcribeAudio).mockResolvedValue(transcription(0.9))
  mockStopRecording.mockResolvedValue(new Blob(['audio']))
})

describe('Chat — resume on mount (T041, FR-022, FR-029)', () => {
  it('restores an existing transcript without re-opening the conversation', async () => {
    await renderResumed()

    expect(await screen.findByText('Hola, ¿qué desea?')).toBeInTheDocument()
    expect(api.streamChatOpen).not.toHaveBeenCalled()
  })

  it('streams the opening line only when the conversation has no messages', async () => {
    vi.mocked(api.getMessages).mockResolvedValue([])

    renderChat()

    await waitFor(() => expect(api.streamChatOpen).toHaveBeenCalledOnce())
  })

  it('restores corrections received in an earlier session', async () => {
    vi.mocked(api.getMessages).mockResolvedValue([existingMessage, existingLearnerMessage])
    vi.mocked(api.getConversationFeedback).mockResolvedValue(
      emptyFeedback({ feedback: [correctionNote] })
    )

    await renderResumed()

    expect(await screen.findByText('yo quiero')).toBeInTheDocument()
    expect(screen.getByRole('note', { name: 'Learning feedback' })).toBeInTheDocument()
  })

  it('reopens into retry mode when a Strict pause was left open', async () => {
    vi.mocked(api.getConversationFeedback).mockResolvedValue(
      emptyFeedback({ awaiting_retry: true, feedback: [correctionNote] })
    )

    await renderResumed()

    await waitFor(() => expect(composer()).toHaveAttribute('placeholder', 'Try again…'))
  })

  it('still shows the transcript when the feedback fetch fails', async () => {
    vi.mocked(api.getConversationFeedback).mockRejectedValue(new Error('offline'))

    await renderResumed()

    expect(await screen.findByText('Hola, ¿qué desea?')).toBeInTheDocument()
  })
})

describe('Chat — turn status (T043, SC-002, SC-004)', () => {
  it('shows the checking indicator and no reply bubble while a corrected turn evaluates', async () => {
    vi.mocked(api.getSettings).mockResolvedValue(settings('strict'))
    const turn = captureTurn()
    await renderResumed()

    sendText('yo querer un cafe')
    turn.userSaved(11)

    expect(await screen.findByText('Checking your sentence…')).toBeInTheDocument()
    // The reply bubble is deferred to the first token: only the opening line
    // and the learner's own message exist so far (R11).
    expect(screen.getAllByRole('article')).toHaveLength(2)
  })

  it('clears the indicator and opens the reply bubble on the first token', async () => {
    vi.mocked(api.getSettings).mockResolvedValue(settings('gentle'))
    const turn = captureTurn()
    await renderResumed()

    sendText('yo querer un cafe')
    turn.userSaved(11)
    await screen.findByText('Checking your sentence…')

    turn.token('Claro,')

    await waitFor(() =>
      expect(screen.queryByText('Checking your sentence…')).not.toBeInTheDocument()
    )
    expect(screen.getByText('Claro,')).toBeInTheDocument()
    expect(screen.getAllByRole('article')).toHaveLength(3)
  })

  it('renders no indicator in Off mode, keeping the send-time placeholder', async () => {
    const turn = captureTurn()
    await renderResumed()

    sendText('un cafe por favor')
    turn.userSaved(11)

    expect(screen.queryByText('Checking your sentence…')).not.toBeInTheDocument()
    // Off keeps today's behaviour: the assistant bubble exists before any token.
    expect(screen.getAllByRole('article')).toHaveLength(3)
  })
})

describe('Chat — feedback frame and retry composer (T055)', () => {
  it('attaches a correction to the learner message it belongs to', async () => {
    vi.mocked(api.getSettings).mockResolvedValue(settings('strict'))
    const turn = captureTurn()
    await renderResumed()

    sendText('yo querer un cafe')
    turn.userSaved(11)
    turn.feedback({ message_id: 11, awaiting_retry: true, notes: [correctionNote] })

    expect(await screen.findByText('yo quiero')).toBeInTheDocument()
    expect(screen.getByRole('note', { name: 'Learning feedback' })).toBeInTheDocument()
  })

  it('switches the composer to retry mode when the turn is flagged', async () => {
    vi.mocked(api.getSettings).mockResolvedValue(settings('strict'))
    const turn = captureTurn()
    await renderResumed()

    sendText('yo querer un cafe')
    turn.userSaved(11)
    turn.feedback({ message_id: 11, awaiting_retry: true, notes: [correctionNote] })

    await waitFor(() => expect(composer()).toHaveAttribute('placeholder', 'Try again…'))
  })

  it('leaves the composer alone when feedback carries no pause', async () => {
    vi.mocked(api.getSettings).mockResolvedValue(settings('gentle'))
    const turn = captureTurn()
    await renderResumed()

    sendText('yo querer un cafe')
    turn.userSaved(11)
    turn.feedback({ message_id: 11, awaiting_retry: false, notes: [] })

    expect(composer()).toHaveAttribute('placeholder', 'Type a message…')
  })

  it('creates no reply bubble when a flagged turn finishes with a null message id', async () => {
    vi.mocked(api.getSettings).mockResolvedValue(settings('strict'))
    const turn = captureTurn()
    await renderResumed()

    sendText('yo querer un cafe')
    turn.userSaved(11)
    turn.feedback({ message_id: 11, awaiting_retry: true, notes: [correctionNote] })
    turn.done(null)

    // FR-016 / FR-020 / SC-005: no assistant row means nothing is ever voiced.
    await waitFor(() => expect(composer()).not.toBeDisabled())
    expect(screen.getAllByRole('article')).toHaveLength(2)
    expect(playedSources).toHaveLength(0)
  })
})

describe('Chat — opening a fresh conversation', () => {
  beforeEach(() => {
    vi.mocked(api.getMessages).mockResolvedValue([])
  })

  it('streams the opening line and then enables the composer', async () => {
    const opening = captureOpening()
    renderChat()
    await waitFor(() => expect(api.streamChatOpen).toHaveBeenCalledOnce())

    opening.token('Buenos días.')
    opening.done(10)

    expect(await screen.findByText('Buenos días.')).toBeInTheDocument()
    expect(await screen.findByLabelText('Type a message')).not.toBeDisabled()
  })

  it('surfaces a failure to open without leaving the composer locked', async () => {
    const opening = captureOpening()
    renderChat()
    await waitFor(() => expect(api.streamChatOpen).toHaveBeenCalledOnce())

    opening.error('Ollama unreachable')

    expect(await screen.findByText(/Ollama unreachable/)).toBeInTheDocument()
    expect(await screen.findByLabelText('Type a message')).not.toBeDisabled()
  })
})

describe('Chat — completing an ordinary reply (FR-021)', () => {
  it('finalizes the reply bubble and voices it', async () => {
    const turn = captureTurn()
    await renderResumed()

    sendText('un cafe por favor')
    turn.userSaved(11)
    turn.token('Claro, ')
    turn.token('aquí tiene.')
    turn.done(12)

    expect(await screen.findByText('Claro, aquí tiene.')).toBeInTheDocument()
    // A Gentle recast rides along with the character's speech and is voiced.
    await waitFor(() => expect(playedSources).toHaveLength(1))
    expect(playedSources[0]).toContain('/api/audio/tts/12')
  })

  it('re-enables the composer when the turn errors', async () => {
    let onError: ((e: string) => void) | undefined
    vi.mocked(api.streamChatMessage).mockImplementation(
      async (_id, _c, _s, _u, _t, _d, error) => {
        onError = error
      }
    )
    await renderResumed()

    sendText('un cafe por favor')
    act(() => onError?.('stream broke'))

    expect(await screen.findByText(/stream broke/)).toBeInTheDocument()
    expect(composer()).not.toBeDisabled()
  })
})

describe('Chat — transcription confidence forwarding (T082, FR-010)', () => {
  const stopRecordingAndWait = async () => {
    fireEvent.click(screen.getByLabelText('Stop recording'))
    await waitFor(() => expect(api.streamChatMessage).toHaveBeenCalled())
  }

  it('forwards a zero confidence rather than dropping it as falsy', async () => {
    isRecording = true
    vi.mocked(api.transcribeAudio).mockResolvedValue(transcription(0.0))
    const turn = captureTurn()
    await renderResumed()

    await stopRecordingAndWait()

    expect(turn.confidenceArg()).toBe(0.0)
  })

  it('forwards an ordinary confidence value', async () => {
    isRecording = true
    vi.mocked(api.transcribeAudio).mockResolvedValue(transcription(0.82))
    const turn = captureTurn()
    await renderResumed()

    await stopRecordingAndWait()

    expect(turn.confidenceArg()).toBe(0.82)
  })

  it('sends no confidence when transcription reports none', async () => {
    isRecording = true
    vi.mocked(api.transcribeAudio).mockResolvedValue(transcription(null))
    const turn = captureTurn()
    await renderResumed()

    await stopRecordingAndWait()

    expect(turn.confidenceArg()).toBeUndefined()
  })

  it('sends no confidence for a typed message', async () => {
    const turn = captureTurn()
    await renderResumed()

    sendText('un cafe por favor')

    await waitFor(() => expect(api.streamChatMessage).toHaveBeenCalled())
    expect(turn.confidenceArg()).toBeUndefined()
  })

  it('asks the learner to retry when nothing could be transcribed', async () => {
    isRecording = true
    vi.mocked(api.transcribeAudio).mockResolvedValue({ ...transcription(0.9), text: '   ' })
    await renderResumed()

    fireEvent.click(screen.getByLabelText('Stop recording'))

    expect(await screen.findByText(/Could not understand audio/)).toBeInTheDocument()
    expect(api.streamChatMessage).not.toHaveBeenCalled()
  })

  it('surfaces a transcription failure instead of sending an empty turn', async () => {
    isRecording = true
    vi.mocked(api.transcribeAudio).mockRejectedValue(new Error('whisper crashed'))
    await renderResumed()

    fireEvent.click(screen.getByLabelText('Stop recording'))

    expect(await screen.findByText(/whisper crashed/)).toBeInTheDocument()
    expect(api.streamChatMessage).not.toHaveBeenCalled()
  })
})

describe('Chat — header, composer and audio controls', () => {
  it('goes home from the back button', async () => {
    await renderResumed()

    fireEvent.click(screen.getByLabelText('Back to Home'))

    expect(mockNavigate).toHaveBeenCalledWith('/')
  })

  it('highlights the back button on hover and restores it on leave', async () => {
    await renderResumed()
    const back = screen.getByLabelText('Back to Home')

    fireEvent.mouseEnter(back)
    expect(back.style.background).toBe('var(--color-bg)')

    fireEvent.mouseLeave(back)
    expect(back.style.background).toBe('none')
  })

  it('completes the conversation and goes home when the chat is ended', async () => {
    vi.mocked(api.completeConversation).mockResolvedValue(conversation)
    await renderResumed()

    fireEvent.click(screen.getByRole('button', { name: 'End Chat' }))

    await waitFor(() => expect(api.completeConversation).toHaveBeenCalledWith(CONV_ID))
    expect(mockNavigate).toHaveBeenCalledWith('/')
  })

  it('still goes home when completing the conversation fails', async () => {
    vi.mocked(api.completeConversation).mockRejectedValue(new Error('offline'))
    await renderResumed()

    fireEvent.click(screen.getByRole('button', { name: 'End Chat' }))

    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/'))
  })

  it('sends on Enter and ignores Shift+Enter', async () => {
    const turn = captureTurn()
    await renderResumed()
    const input = composer()

    fireEvent.change(input, { target: { value: 'hola' } })
    fireEvent.keyDown(input, { key: 'Enter', shiftKey: true })
    expect(api.streamChatMessage).not.toHaveBeenCalled()

    fireEvent.keyDown(input, { key: 'Enter' })
    await waitFor(() => expect(api.streamChatMessage).toHaveBeenCalled())
    expect(turn.confidenceArg()).toBeUndefined()
  })

  it('ignores an Enter press on an empty composer', async () => {
    await renderResumed()

    fireEvent.keyDown(composer(), { key: 'Enter' })

    expect(api.streamChatMessage).not.toHaveBeenCalled()
  })

  it('toggles the expression helper open and shut', async () => {
    await renderResumed()

    fireEvent.click(screen.getByLabelText('Open expression helper'))
    expect(screen.getByLabelText('Close expression helper')).toBeInTheDocument()

    fireEvent.click(screen.getByLabelText('Close expression helper'))
    expect(screen.getByLabelText('Open expression helper')).toBeInTheDocument()
  })

  it('replays a reply at normal speed', async () => {
    await renderResumed()
    await screen.findByText('Hola, ¿qué desea?')

    fireEvent.click(screen.getByLabelText('Replay'))

    await waitFor(() => expect(playedSources[playedSources.length - 1]).toContain('/api/audio/tts/10'))
  })

  it('replays a reply at slower speed', async () => {
    await renderResumed()
    await screen.findByText('Hola, ¿qué desea?')

    fireEvent.click(screen.getByLabelText('Play slower'))

    await waitFor(() => expect(playedSources[playedSources.length - 1]).toContain('/api/audio/tts/10'))
  })

  it('starts recording from the record button', async () => {
    await renderResumed()

    fireEvent.click(screen.getByLabelText('Start recording'))

    expect(screen.getByLabelText('Start recording')).toBeInTheDocument()
  })

  it('dismisses a turn error banner', async () => {
    let onError: ((e: string) => void) | undefined
    vi.mocked(api.streamChatMessage).mockImplementation(
      async (_id, _c, _s, _u, _t, _d, error) => {
        onError = error
      }
    )
    await renderResumed()
    sendText('hola')
    act(() => onError?.('stream broke'))
    await screen.findByText(/stream broke/)

    fireEvent.click(screen.getByRole('button', { name: /dismiss/i }))

    await waitFor(() => expect(screen.queryByText(/stream broke/)).not.toBeInTheDocument())
  })
})
