import type { SettingScope } from '../../hooks/podcasts/useSeriesScopes'
import ConfirmDialog from '../shared/ConfirmDialog'

interface ScopeDialogProps {
  /** The setting's legend, such as "Style". */
  setting: string
  onAnswer: (scope: SettingScope) => void
  /** Escape: the change is reverted. */
  onCancel: () => void
}

/** The scope question on a continuing series' first change of a setting (011 FR-016). Built on
 * ConfirmDialog, so it keeps focus inside and gives it back to the changed control. */
export default function ScopeDialog({ setting, onAnswer, onCancel }: ScopeDialogProps) {
  return (
    <ConfirmDialog title="Change for which episodes?" message={`${setting} can change for this episode only, or for this and every later episode of the series.`}
      cancelLabel="Just this episode" confirmLabel="This and later episodes"
      onCancel={() => onAnswer('this-episode')} onConfirm={() => onAnswer('from-now-on')} onEscape={onCancel} />
  )
}
