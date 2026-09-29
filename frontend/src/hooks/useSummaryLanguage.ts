import { useEffect, useState } from 'react'
import * as api from '../services/api'
import type { SummaryLanguage } from '../services/api'

const DEFAULT_SUMMARY_LANGUAGE: SummaryLanguage = 'conversation'

/** The learner's last choice of summary language, remembered across conversations (FR-040). */
export function useSummaryLanguage(): [SummaryLanguage, (language: SummaryLanguage) => void] {
  const [language, setLanguage] = useState<SummaryLanguage>(DEFAULT_SUMMARY_LANGUAGE)
  useEffect(() => {
    let isCurrent = true
    api
      .getSettings()
      .then((settings) => isCurrent && setLanguage(settings.summary_language ?? DEFAULT_SUMMARY_LANGUAGE))
      .catch(() => undefined)
    return () => {
      isCurrent = false
    }
  }, [])
  const choose = (next: SummaryLanguage) => {
    setLanguage(next)
    void api.updateSettings({ summary_language: next }).catch(() => undefined)
  }
  return [language, choose]
}
