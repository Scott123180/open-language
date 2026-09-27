import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import * as flashcardsApi from '../../services/flashcardsApi'
import { useWordAudio } from './useWordAudio'

vi.mock('../../services/flashcardsApi')

const URL = '/api/flashcards/tts/3'
const played: { src: string; rate: number }[] = []
let playResult: Promise<void> = Promise.resolve()

class FakeAudio {
  playbackRate = 1
  constructor(public src: string) {}
  play() {
    played.push({ src: this.src, rate: this.playbackRate })
    return playResult
  }
}

describe('useWordAudio', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    played.length = 0
    playResult = Promise.resolve()
    vi.stubGlobal('Audio', FakeAudio)
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('plays the word at the requested rate', async () => {
    const { result } = renderHook(() => useWordAudio(URL))

    await act(() => result.current.play(0.6))

    expect(played).toEqual([{ src: URL, rate: 0.6 }])
    expect(result.current.failureMessage).toBeNull()
  })

  it('explains a failed play with the server\'s reason', async () => {
    playResult = Promise.reject(new Error('NotSupportedError'))
    vi.mocked(flashcardsApi.describeAudioFailure).mockResolvedValue("The German voice isn't installed.")
    const { result } = renderHook(() => useWordAudio(URL))

    await act(() => result.current.play(1.0))

    await waitFor(() =>
      expect(result.current.failureMessage).toBe("The German voice isn't installed."),
    )
    expect(flashcardsApi.describeAudioFailure).toHaveBeenCalledWith(URL)
  })

  it('clears the failure when a later play works', async () => {
    playResult = Promise.reject(new Error('fail'))
    vi.mocked(flashcardsApi.describeAudioFailure).mockResolvedValue('No audio.')
    const { result } = renderHook(() => useWordAudio(URL))
    await act(() => result.current.play(1.0))
    playResult = Promise.resolve()

    await act(() => result.current.play(1.0))

    expect(result.current.failureMessage).toBeNull()
  })
})
