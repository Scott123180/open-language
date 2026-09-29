import { useState } from 'react'
import type {
  EpisodeLengthId,
  PodcastCatalog,
  PodcastFormatId,
  PodcastPreferences,
} from '../../services/podcastsApi'

const FIRST_FORMAT: PodcastFormatId = 'one_host'

export interface SetupForm {
  format: PodcastFormatId
  setFormat: (format: PodcastFormatId) => void
  length: EpisodeLengthId
  setLength: (length: EpisodeLengthId) => void
  learnerName: string
  setLearnerName: (name: string) => void
}

/** The format starts on the last one used (FR-005), the length on the default, the name on
 * the one remembered (FR-011). Until the learner changes a field it follows the loaded data. */
export function useSetupForm(catalog?: PodcastCatalog, preferences?: PodcastPreferences): SetupForm {
  const [format, setFormat] = useState<PodcastFormatId | null>(null)
  const [length, setLength] = useState<EpisodeLengthId | null>(null)
  const [learnerName, setLearnerName] = useState<string | null>(null)
  const defaultLength = catalog?.lengths.find((option) => option.is_default)?.length_id ?? 'medium'
  return {
    format: format ?? preferences?.last_format ?? FIRST_FORMAT,
    setFormat,
    length: length ?? defaultLength,
    setLength,
    learnerName: learnerName ?? preferences?.learner_name ?? '',
    setLearnerName,
  }
}
