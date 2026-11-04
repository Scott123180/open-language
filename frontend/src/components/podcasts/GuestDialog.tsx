import { useState } from 'react'
import type { PersonalityOption, SeriesHostView } from '../../services/podcastsApi'
import ConfirmDialog from '../shared/ConfirmDialog'
import SettingFieldset from './SettingFieldset'

const ANY = 'any'

interface GuestDialogProps {
  /** The regular host whose chair the guest takes for this episode. */
  host: SeriesHostView
  /** The host beside the guest today, whose personality the guest cannot share. */
  otherHost: SeriesHostView | undefined
  personalities: PersonalityOption[]
  onInvite: (personalityId: string | null) => void
  onCancel: () => void
}

/** Invite a guest…: one episode only, so the regular host is back next time (011 FR-020). */
export default function GuestDialog({ host, otherHost, personalities, onInvite, onCancel }: GuestDialogProps) {
  const [choice, setChoice] = useState(ANY)
  const tiles = [{ value: ANY, label: 'Any', detail: '' }, ...personalities
    .filter((option) => option.personality_id !== otherHost?.personality_id)
    .map((option) => ({ value: option.personality_id, label: option.label, detail: option.description }))]
  const message = `${host.name} is away for this episode only and back next time. The guest doesn't know the earlier episodes.`
  return (
    <ConfirmDialog title={`Invite a guest in place of ${host.name}?`} message={message} confirmLabel="Invite"
      onConfirm={() => onInvite(choice === ANY ? null : choice)} onCancel={onCancel}>
      <SettingFieldset legend="The guest's personality" options={tiles} value={choice} onChange={setChoice} />
    </ConfirmDialog>
  )
}
