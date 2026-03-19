import { createContext, useContext, useState, ReactNode } from 'react'

export interface ConversationMessage {
  id: number | null
  role: 'user' | 'assistant'
  content: string
  inputSource?: 'voice' | 'keyboard'
  isStreaming?: boolean
}

interface ConversationState {
  conversationId: number | null
  messages: ConversationMessage[]
  isLoading: boolean
  error: string | null
}

interface ConversationActions {
  setConversationId: (id: number) => void
  addMessage: (msg: ConversationMessage) => void
  updateLastMessage: (content: string) => void
  finalizeLastMessage: (id: number) => void
  setLoading: (v: boolean) => void
  setError: (e: string | null) => void
  reset: () => void
}

type ConversationContextValue = ConversationState & ConversationActions

const ConversationContext = createContext<ConversationContextValue | null>(null)

const initialState: ConversationState = {
  conversationId: null,
  messages: [],
  isLoading: false,
  error: null,
}

export function ConversationProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<ConversationState>(initialState)

  const setConversationId = (id: number) =>
    setState((s) => ({ ...s, conversationId: id }))

  const addMessage = (msg: ConversationMessage) =>
    setState((s) => ({ ...s, messages: [...s.messages, msg] }))

  const updateLastMessage = (content: string) =>
    setState((s) => {
      const messages = [...s.messages]
      if (messages.length === 0) return s
      messages[messages.length - 1] = { ...messages[messages.length - 1], content }
      return { ...s, messages }
    })

  const finalizeLastMessage = (id: number) =>
    setState((s) => {
      const messages = [...s.messages]
      if (messages.length === 0) return s
      messages[messages.length - 1] = { ...messages[messages.length - 1], id, isStreaming: false }
      return { ...s, messages }
    })

  const setLoading = (v: boolean) => setState((s) => ({ ...s, isLoading: v }))
  const setError = (e: string | null) => setState((s) => ({ ...s, error: e }))
  const reset = () => setState(initialState)

  const value: ConversationContextValue = {
    ...state,
    setConversationId,
    addMessage,
    updateLastMessage,
    finalizeLastMessage,
    setLoading,
    setError,
    reset,
  }

  return ConversationContext.Provider({ value, children })
}

export function useConversation(): ConversationContextValue {
  const ctx = useContext(ConversationContext)
  if (!ctx) throw new Error('useConversation must be used within ConversationProvider')
  return ctx
}
