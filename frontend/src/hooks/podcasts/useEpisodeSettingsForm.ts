import { useState } from 'react'
import type {
  EpisodeOptions,
  EpisodeSettingsRequest,
  EpisodeStyleId,
  HostLineLengthId,
  InviteFrequencyId,
  LearnerRole,
  PodcastPreferences,
  SeriesSettingName,
  SeriesSettings,
} from '../../services/podcastsApi'
import type { SettingScope } from './useSeriesScopes'

export interface EpisodeSettingValues {
  style: EpisodeStyleId
  line_length: HostLineLengthId
  invite_frequency: InviteFrequencyId
  learner_role: LearnerRole
  today_subject: string
}

export type EpisodeSettingName = keyof EpisodeSettingValues

export interface EpisodeSettingsForm {
  values: EpisodeSettingValues
  /** "Balanced · Medium lines · Asked sometimes": the disclosure's name. */
  summary: string
  change: <K extends EpisodeSettingName>(name: K, value: EpisodeSettingValues[K]) => void
  requestSettings: () => EpisodeSettingsRequest
  /** 011: a continuing series' scope of each changed setting. */
  scopeOf?: (name: SeriesSettingName) => SettingScope | undefined
  reset: () => void
}

/** Episode settings start on the last one-off's style, lines and frequency (FR-013), Your role on
 * the show's own, and Today's subject empty; a continuing series starts on its usual settings
 * (011 FR-015). Until a field changes it follows the loaded data. */
export function useEpisodeSettingsForm(
  options: EpisodeOptions | undefined,
  preferences: PodcastPreferences | undefined,
  showRole: LearnerRole,
  usual?: SeriesSettings,
): EpisodeSettingsForm {
  const [changed, setChanged] = useState<Partial<EpisodeSettingValues>>({})
  const starting = usual ? usualValues(usual) : startingValues(options, preferences, showRole)
  const values = { ...starting, ...changed }
  return {
    values,
    summary: settingsSummary(values, options),
    change: (name, value) => setChanged((current) => ({ ...current, [name]: value })),
    requestSettings: () => ({ ...values, today_subject: values.today_subject.trim() || null }),
    reset: () => setChanged({}),
  }
}

function usualValues(usual: SeriesSettings): EpisodeSettingValues {
  const { style, line_length, invite_frequency, learner_role } = usual
  return { style, line_length, invite_frequency, learner_role, today_subject: '' }
}

function startingValues(options: EpisodeOptions | undefined, preferences: PodcastPreferences | undefined, showRole: LearnerRole): EpisodeSettingValues {
  return {
    style: preferences?.last_style ?? defaultOf(options?.styles, 'style_id') ?? 'balanced',
    line_length: preferences?.last_line_length ?? defaultOf(options?.line_lengths, 'line_length_id') ?? 'medium',
    invite_frequency: preferences?.last_invite_frequency ?? defaultOf(options?.invite_frequencies, 'invite_frequency_id') ?? 'sometimes',
    learner_role: showRole,
    today_subject: '',
  }
}

function defaultOf<T extends { is_default: boolean }, K extends keyof T>(items: T[] | undefined, key: K): T[K] | undefined {
  return items?.find((item) => item.is_default)?.[key]
}

/** The one-line summary, from the catalogue's labels. */
export function settingsSummary(values: EpisodeSettingValues, options: EpisodeOptions | undefined): string {
  const style = options?.styles.find((s) => s.style_id === values.style)?.label ?? values.style
  const lines = options?.line_lengths.find((l) => l.line_length_id === values.line_length)?.label ?? values.line_length
  const asked = options?.invite_frequencies.find((f) => f.invite_frequency_id === values.invite_frequency)?.label ?? values.invite_frequency
  return `${style} · ${lines} lines · Asked ${asked.toLowerCase()}`
}
