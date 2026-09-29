import { useCallback, useEffect, useState } from 'react'
import * as api from '../services/api'
import type { ConversationSummary } from '../services/api'

export interface SummaryState {
  summary: ConversationSummary | null
  error: string | null
  isLoading: boolean
  retry: () => void
}

/**
 * The conversation's summary, fetched only while the panel is open and again when a line has
 * been added (FR-042). Reading it never touches the conversation itself (FR-041).
 */
export function useConversationSummary(
  conversationId: number,
  isOpen: boolean,
  lastMessageId?: number,
): SummaryState {
  const [summary, setSummary] = useState<ConversationSummary | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    if (!isOpen) return
    return fetchSummary(conversationId, setSummary, setError)
  }, [conversationId, isOpen, lastMessageId, attempt])
  const retry = useCallback(() => setAttempt((count) => count + 1), [])
  return { summary, error, isLoading: isOpen && !summary && !error, retry }
}

function fetchSummary(
  conversationId: number,
  setSummary: (summary: ConversationSummary) => void,
  setError: (error: string | null) => void,
): () => void {
  let isCurrent = true
  setError(null)
  api
    .getConversationSummary(conversationId)
    .then((summary) => isCurrent && setSummary(summary))
    .catch((e: Error) => isCurrent && setError(e.message))
  return () => {
    isCurrent = false
  }
}
