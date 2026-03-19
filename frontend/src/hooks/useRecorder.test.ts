import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useRecorder } from './useRecorder'

const mockStop = vi.fn()
const mockStart = vi.fn()
const mockGetTracks = vi.fn(() => [{ stop: vi.fn() }])

const mockMediaRecorder = {
  start: mockStart,
  stop: mockStop,
  ondataavailable: null as unknown,
  onstop: null as unknown,
  state: 'inactive' as string,
}

vi.stubGlobal('MediaRecorder', Object.assign(vi.fn(() => mockMediaRecorder), {
  isTypeSupported: vi.fn(() => false),
}))

vi.stubGlobal('navigator', {
  mediaDevices: {
    getUserMedia: vi.fn().mockResolvedValue({
      getTracks: mockGetTracks,
    }),
  },
})

describe('useRecorder', () => {
  beforeEach(() => {
    mockStart.mockClear()
    mockStop.mockClear()
    mockGetTracks.mockClear()
    ;(navigator.mediaDevices.getUserMedia as ReturnType<typeof vi.fn>).mockClear()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('isRecording is false initially', () => {
    const { result } = renderHook(() => useRecorder())
    expect(result.current.isRecording).toBe(false)
  })

  it('startRecording calls navigator.mediaDevices.getUserMedia with { audio: true }', async () => {
    const { result } = renderHook(() => useRecorder())
    await act(async () => {
      await result.current.startRecording()
    })
    expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledWith({ audio: true })
  })

  it('startRecording calls MediaRecorder.start()', async () => {
    const { result } = renderHook(() => useRecorder())
    await act(async () => {
      await result.current.startRecording()
    })
    expect(mockStart).toHaveBeenCalledWith(100)
  })

  it('isRecording is true after startRecording', async () => {
    const { result } = renderHook(() => useRecorder())
    await act(async () => {
      await result.current.startRecording()
    })
    expect(result.current.isRecording).toBe(true)
  })

  it('stopRecording calls mediaRecorder.stop()', async () => {
    const { result } = renderHook(() => useRecorder())
    await act(async () => {
      await result.current.startRecording()
    })
    act(() => {
      result.current.stopRecording()
    })
    expect(mockStop).toHaveBeenCalledTimes(1)
  })

  it('isRecording becomes false after onstop fires', async () => {
    const { result } = renderHook(() => useRecorder())
    await act(async () => {
      await result.current.startRecording()
    })
    let blobResult: Blob | undefined
    act(() => {
      result.current.stopRecording().then((b) => { blobResult = b })
    })
    await act(async () => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const onstop = mockMediaRecorder.onstop as any
      onstop?.()
    })
    expect(result.current.isRecording).toBe(false)
    expect(blobResult).toBeInstanceOf(Blob)
  })
})
