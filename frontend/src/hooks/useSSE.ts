import { useState, useRef } from 'react'

export interface SSEOptions {
  onToken: (token: string) => void
  onDone: (data: Record<string, unknown>) => void
  onError: (error: Error) => void
}

export interface UseSSEResult {
  stream: (url: string, options: RequestInit, sseOptions: SSEOptions) => Promise<void>
  cancel: () => void
  isStreaming: boolean
}

export function useSSE(): UseSSEResult {
  const [isStreaming, setIsStreaming] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  const cancel = () => {
    abortRef.current?.abort()
    abortRef.current = null
    setIsStreaming(false)
  }

  const stream = async (url: string, options: RequestInit, sseOptions: SSEOptions): Promise<void> => {
    const controller = new AbortController()
    abortRef.current = controller
    setIsStreaming(true)

    try {
      const res = await fetch(url, { ...options, signal: controller.signal })
      if (!res.ok || !res.body) {
        throw new Error(`HTTP ${res.status}`)
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      for (;;) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const raw = line.slice(6).trim()
          if (raw === '[DONE]') continue
          try {
            const parsed: Record<string, unknown> = JSON.parse(raw)
            if (parsed.token !== undefined) {
              sseOptions.onToken(String(parsed.token))
            } else if (parsed.done) {
              sseOptions.onDone(parsed)
            }
          } catch {
            // ignore malformed lines
          }
        }
      }
    } catch (e) {
      if (e instanceof Error && e.name !== 'AbortError') {
        sseOptions.onError(e)
      }
    } finally {
      setIsStreaming(false)
    }
  }

  return { stream, cancel, isStreaming }
}
