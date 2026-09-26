import { useEffect, useState } from 'react'
import * as api from '../../services/api'
import type { ConversationLevelId, ConversationLevelOption } from '../../services/api'
import { useConversationLevels } from '../../hooks/useConversationLevels'

interface SaveStatus {
  isSaving: boolean
  announcement: string | null
  error: string | null
}

export interface ConversationLevelSetting extends SaveStatus {
  levels: ConversationLevelOption[]
  // Null until the stored level has loaded.
  level: ConversationLevelId | null
  changeLevel: (next: ConversationLevelId) => Promise<void>
}

type LevelSetter = (level: ConversationLevelId | null) => void

const IDLE: SaveStatus = { isSaving: false, announcement: null, error: null }
const SAVE_FAILED =
  'The level was not changed. Check that the app is still running, then try again.'
const LOAD_FAILED = 'Your conversation level could not be loaded. Reload the page to try again.'

/** The learner-wide level, changed and saved from the conversation screen (FR-006, FR-010). */
export function useConversationLevelSetting(): ConversationLevelSetting {
  const catalogue = useConversationLevels()
  const [level, setLevel] = useState<ConversationLevelId | null>(null)
  const loadError = useStoredLevel(setLevel)
  const { status, changeLevel } = useLevelSave(catalogue.levels, level, setLevel)
  const error = status.error ?? loadError ?? catalogue.error
  return { levels: catalogue.levels, level, ...status, error, changeLevel }
}

function useStoredLevel(onLoad: LevelSetter): string | null {
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    api
      .getSettings()
      .then((settings) => onLoad(settings.conversation_level))
      .catch(() => setError(LOAD_FAILED))
  }, [onLoad])
  return error
}

function useLevelSave(
  levels: ConversationLevelOption[],
  level: ConversationLevelId | null,
  setLevel: LevelSetter
) {
  const [status, setStatus] = useState<SaveStatus>(IDLE)
  const changeLevel = async (next: ConversationLevelId) => {
    setLevel(next)
    setStatus({ ...IDLE, isSaving: true })
    try {
      await api.updateSettings({ conversation_level: next })
      setStatus({ ...IDLE, announcement: announce(levels, next) })
    } catch {
      setLevel(level)
      setStatus({ ...IDLE, error: SAVE_FAILED })
    }
  }
  return { status, changeLevel }
}

function announce(levels: ConversationLevelOption[], levelId: ConversationLevelId): string {
  const label = levels.find((option) => option.level_id === levelId)?.label ?? levelId
  return `Level set to ${label}. It applies from the next reply.`
}
