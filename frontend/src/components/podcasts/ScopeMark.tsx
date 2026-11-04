import type { SettingScope } from '../../hooks/podcasts/useSeriesScopes'
import { mutedTextStyle } from './styles'

const SCOPE_TEXT: Record<SettingScope, string> = {
  'this-episode': 'this episode',
  'from-now-on': 'from now on',
}

/** After a setting's legend: which episodes its change is for (011 FR-016). */
export default function ScopeMark({ scope }: { scope: SettingScope | undefined }) {
  if (!scope) return null
  return <span style={{ ...mutedTextStyle, fontWeight: 'normal' }}>{` · ${SCOPE_TEXT[scope]}`}</span>
}
