import type { SeriesSettingName } from '../../services/podcastsApi'
import type { EpisodeSettingName, EpisodeSettingsForm } from './useEpisodeSettingsForm'
import type { SetupForm } from './useSetupForm'
import type { SeriesScopes } from './useSeriesScopes'

const KEPT_EPISODE_SETTINGS: ReadonlySet<EpisodeSettingName> = new Set(['style', 'line_length', 'invite_frequency', 'learner_role'])

/** The setup form with every series setting's change sent through the scope question first
 * (011 FR-016). Today's subject and the name are this episode's only, so they never ask. */
export function useScopedSetupForm(form: SetupForm, scopes: SeriesScopes): SetupForm {
  return {
    ...form,
    setFormat: (format) => scopes.request('format', format, () => form.setFormat(format)),
    setLength: (length) => scopes.request('length', length, () => form.setLength(length)),
    settings: scopedSettings(form.settings, scopes),
    scopeOf: scopes.scopeOf,
    reset: () => {
      scopes.clear()
      form.reset()
    },
  }
}

function scopedSettings(settings: EpisodeSettingsForm, scopes: SeriesScopes): EpisodeSettingsForm {
  return {
    ...settings,
    scopeOf: scopes.scopeOf,
    change: (name, value) => {
      if (!KEPT_EPISODE_SETTINGS.has(name)) return settings.change(name, value)
      scopes.request(name as SeriesSettingName, value, () => settings.change(name, value))
    },
  }
}
