import { useEffect, useState } from 'react'
import * as api from '../services/api'

export interface ConversationLevelsState {
  levels: api.ConversationLevelOption[]
  isLoading: boolean
  error: string | null
}

const LOAD_ERROR = 'Conversation levels could not be loaded. Reload the page to try again.'

/** The level catalogue, shared by the Settings fieldset and the chat header control. */
export function useConversationLevels(): ConversationLevelsState {
  const [state, setState] = useState<ConversationLevelsState>({
    levels: [],
    isLoading: true,
    error: null,
  })

  useEffect(() => {
    api
      .getConversationLevels()
      .then((levels) => setState({ levels, isLoading: false, error: null }))
      .catch(() => setState({ levels: [], isLoading: false, error: LOAD_ERROR }))
  }, [])

  return state
}
