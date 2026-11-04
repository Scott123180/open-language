import { useState } from 'react'
import type {
  EpisodeKind,
  EpisodeLengthId,
  LearnerRole,
  PodcastCatalog,
  PodcastFormatId,
  PodcastPreferences,
  SeriesSettingName,
  SeriesSettings,
} from '../../services/podcastsApi'
import { useEpisodeSettingsForm } from './useEpisodeSettingsForm'
import type { EpisodeSettingsForm } from './useEpisodeSettingsForm'
import type { SettingScope } from './useSeriesScopes'

const FIRST_FORMAT: PodcastFormatId = 'one_host'

export interface SetupForm {
  format: PodcastFormatId
  setFormat: (format: PodcastFormatId) => void
  length: EpisodeLengthId
  setLength: (length: EpisodeLengthId) => void
  learnerName: string
  setLearnerName: (name: string) => void
  /** The next series episode by default; a one-off on request (010 FR-002). */
  kind: EpisodeKind
  setKind: (kind: EpisodeKind) => void
  /** 011: Episode settings, behind their disclosure. */
  settings: EpisodeSettingsForm
  /** 011: a continuing series' scope of each changed setting, shown beside its legend. */
  scopeOf?: (name: SeriesSettingName) => SettingScope | undefined
  /** 011: forget every change, so the form follows the loaded settings again. */
  reset: () => void
}

/** The format starts on the last one used (FR-005), the length on the default, the name on
 * the one remembered (FR-011); a continuing series starts on its usual settings instead (011
 * FR-015). Until the learner changes a field it follows the loaded data. */
export function useSetupForm(catalog?: PodcastCatalog, preferences?: PodcastPreferences, showRole: LearnerRole = 'guest', usual?: SeriesSettings): SetupForm {
  const [format, setFormat] = useState<PodcastFormatId | null>(null)
  const [length, setLength] = useState<EpisodeLengthId | null>(null)
  const [learnerName, setLearnerName] = useState<string | null>(null)
  const [kind, setKind] = useState<EpisodeKind>('series')
  const series = kind === 'series' ? usual : undefined
  const settings = useEpisodeSettingsForm(catalog?.episode_options, preferences, showRole, series)
  const starting = startingFields(catalog, preferences, series)
  const reset = () => {
    setFormat(null)
    setLength(null)
    settings.reset()
  }
  return {
    ...{ settings, setFormat, setLength, setLearnerName, kind, setKind, reset },
    format: format ?? starting.format,
    length: length ?? starting.length,
    learnerName: learnerName ?? preferences?.learner_name ?? '',
  }
}

/** A continuing series' usual format and length, or the last format and the default length. */
function startingFields(catalog?: PodcastCatalog, preferences?: PodcastPreferences, series?: SeriesSettings) {
  const defaultLength = catalog?.lengths.find((option) => option.is_default)?.length_id ?? 'medium'
  return {
    format: series?.format ?? preferences?.last_format ?? FIRST_FORMAT,
    length: series?.length ?? defaultLength,
  }
}
