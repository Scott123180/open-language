import { useState } from 'react'
import type { SeriesSettingName, SeriesSettings } from '../../services/podcastsApi'

export type SettingScope = 'this-episode' | 'from-now-on'

/** Each series setting's legend on the setup screen, for the scope question. */
export const SERIES_SETTING_LEGENDS: Record<SeriesSettingName, string> = {
  format: 'Format',
  length: 'Length',
  style: 'Style',
  line_length: 'Host lines',
  invite_frequency: "How often you're asked",
  learner_role: 'Your role',
}

interface PendingChange {
  name: SeriesSettingName
  apply: () => void
}

export interface SeriesScopes {
  scopeOf: (name: SeriesSettingName) => SettingScope | undefined
  /** Change a setting: at once when its scope is known, otherwise after the question. */
  request: (name: SeriesSettingName, value: string, apply: () => void) => void
  /** The setting whose scope is being asked, or null. */
  asking: SeriesSettingName | null
  answer: (scope: SettingScope) => void
  /** Escape or Cancel: the change is reverted, so it is never applied. */
  cancel: () => void
  fromNowOn: () => SeriesSettingName[]
  clear: () => void
}

/** Each change of a continuing series' setting asks once whether it is for this episode only
 * or for later ones too (011 FR-016, data-model §6.1). `usual` is null on episode 1, where
 * every choice becomes the series' usual setting, so nothing is asked. */
export function useSeriesScopes(usual: SeriesSettings | null): SeriesScopes {
  const [scopes, setScopes] = useState<Partial<Record<SeriesSettingName, SettingScope>>>({})
  const pending = usePendingChange()
  const setScope = (name: SeriesSettingName, scope: SettingScope | undefined) =>
    setScopes((current) => ({ ...current, [name]: scope }))
  const request = (name: SeriesSettingName, value: string, apply: () => void) => {
    if (usual !== null && usual[name] === value) setScope(name, undefined)
    if (usual === null || usual[name] === value || scopes[name]) return apply()
    pending.hold({ name, apply })
  }
  return {
    scopeOf: (name) => scopes[name],
    request,
    asking: pending.name,
    answer: (scope) => pending.settle((name) => setScope(name, scope)),
    cancel: pending.drop,
    fromNowOn: () => (Object.keys(scopes) as SeriesSettingName[]).filter((name) => scopes[name] === 'from-now-on'),
    clear: () => setScopes({}),
  }
}

/** The change waiting on the scope question: applied once answered, dropped on Escape. */
function usePendingChange() {
  const [pending, setPending] = useState<PendingChange | null>(null)
  return {
    name: pending?.name ?? null,
    hold: setPending,
    settle: (onScope: (name: SeriesSettingName) => void) => {
      if (!pending) return
      onScope(pending.name)
      pending.apply()
      setPending(null)
    },
    drop: () => setPending(null),
  }
}
