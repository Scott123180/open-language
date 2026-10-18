import { useState } from 'react'
import type { PersonalityOption, SeriesHostView } from '../../services/podcastsApi'
import ConfirmDialog from '../shared/ConfirmDialog'
import ErrorBanner from '../shared/ErrorBanner'
import ThemedSelect from '../shared/ThemedSelect'
import { mutedTextStyle } from './styles'

const ANY = 'any'

interface RecastDialogProps {
  host: SeriesHostView
  otherHost: SeriesHostView | undefined
  personalities: PersonalityOption[]
  /** With two installed voices, the new host usually speaks with this host's voice. */
  keepsVoice: boolean
  isBusy: boolean
  error: string | null
  onConfirm: (personalityId: string | null) => void
  onCancel: () => void
}

/** Recast asks first: the new host joins without the earlier history (FR-009). */
export default function RecastDialog(props: RecastDialogProps) {
  const [choice, setChoice] = useState(ANY)
  const options = [{ value: ANY, label: 'Any' }, ...props.personalities
    .filter((option) => option.personality_id !== props.otherHost?.personality_id)
    .map((option) => ({ value: option.personality_id, label: option.label }))]
  const message = `${props.host.name} will leave the show. The new host joins without the earlier history: they won't know what was said in earlier episodes.`
  return (
    <ConfirmDialog title={`Recast ${props.host.name}?`} message={message} confirmLabel="Recast" isBusy={props.isBusy}
      onConfirm={() => props.onConfirm(choice === ANY ? null : choice)} onCancel={props.onCancel}>
      <ThemedSelect label="The new host's personality" value={choice} options={options} onChange={setChoice} />
      {props.keepsVoice && <p style={{ ...mutedTextStyle, margin: 0 }}>The new host keeps this voice: only two voices are installed for this language.</p>}
      {props.error && <ErrorBanner message={props.error} />}
    </ConfirmDialog>
  )
}
