import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useSSE } from './useSSE'

function makeStream(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder()
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk))
      }
      controller.close()
    },
  })
}

const SSE_BODY =
  'data: {"token":"Hello"}\n\ndata: {"token":" world"}\n\ndata: {"done":true,"message_id":42}\n\n'

beforeEach(() => {
  vi.restoreAllMocks()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('useSSE', () => {
  it('calls onToken for each token in the SSE stream', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      body: makeStream([SSE_BODY]),
    })
    vi.stubGlobal('fetch', mockFetch)

    const { result } = renderHook(() => useSSE())
    const onToken = vi.fn()
    const onDone = vi.fn()
    const onError = vi.fn()

    await act(async () => {
      await result.current.stream('/api/test', { method: 'POST' }, { onToken, onDone, onError })
    })

    expect(onToken).toHaveBeenCalledWith('Hello')
    expect(onToken).toHaveBeenCalledWith(' world')
    expect(onToken).toHaveBeenCalledTimes(2)
  })

  it('calls onDone when done:true data is received', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      body: makeStream([SSE_BODY]),
    })
    vi.stubGlobal('fetch', mockFetch)

    const { result } = renderHook(() => useSSE())
    const onToken = vi.fn()
    const onDone = vi.fn()
    const onError = vi.fn()

    await act(async () => {
      await result.current.stream('/api/test', { method: 'POST' }, { onToken, onDone, onError })
    })

    expect(onDone).toHaveBeenCalledTimes(1)
    expect(onDone).toHaveBeenCalledWith(expect.objectContaining({ done: true, message_id: 42 }))
  })

  it('calls onError when fetch rejects', async () => {
    const mockFetch = vi.fn().mockRejectedValue(new Error('Network failure'))
    vi.stubGlobal('fetch', mockFetch)

    const { result } = renderHook(() => useSSE())
    const onToken = vi.fn()
    const onDone = vi.fn()
    const onError = vi.fn()

    await act(async () => {
      await result.current.stream('/api/test', { method: 'POST' }, { onToken, onDone, onError })
    })

    expect(onError).toHaveBeenCalledTimes(1)
    expect(onError).toHaveBeenCalledWith(expect.any(Error))
  })

  it('cancel() aborts the stream', async () => {
    let capturedSignal: AbortSignal | undefined

    const mockFetch = vi.fn().mockImplementation((_url: string, opts: RequestInit) => {
      capturedSignal = opts.signal as AbortSignal
      return new Promise(() => {}) // never resolves
    })
    vi.stubGlobal('fetch', mockFetch)

    const { result } = renderHook(() => useSSE())
    const onToken = vi.fn()
    const onDone = vi.fn()
    const onError = vi.fn()

    act(() => {
      result.current.stream('/api/test', { method: 'POST' }, { onToken, onDone, onError })
    })

    act(() => {
      result.current.cancel()
    })

    expect(capturedSignal?.aborted).toBe(true)
  })

  it('isStreaming is true while streaming and false after completion', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      body: makeStream([SSE_BODY]),
    })
    vi.stubGlobal('fetch', mockFetch)

    const { result } = renderHook(() => useSSE())

    await act(async () => {
      await result.current.stream(
        '/api/test',
        { method: 'POST' },
        { onToken: vi.fn(), onDone: vi.fn(), onError: vi.fn() },
      )
    })

    expect(result.current.isStreaming).toBe(false)
  })
})
