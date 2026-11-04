import { useState } from 'react'
import type { HostSlot, PersonalityOption, PodcastFormatId, SeriesHostView } from '../../services/podcastsApi'
import type { GuestControls } from '../../hooks/podcasts/useGuest'
import { useRecast } from '../../hooks/podcasts/useRecast'
import GuestCard from './GuestCard'
import GuestDialog from './GuestDialog'
import RecastDialog from './RecastDialog'
import SeriesHostCard from './SeriesHostCard'

interface SeriesHostsProps {
  hosts: SeriesHostView[]
  hostCount: number
  personalities: PersonalityOption[]
  keepsVoice: boolean
  series: { seriesId: number; language: string; learnerName: string }
  /** 011: today's guest, who takes a chair for this episode only. */
  guest?: GuestControls
  /** 011: the format a guest is cast for. */
  format?: PodcastFormatId
  onPlaySample: (host: SeriesHostView) => void
}

/** The series' hosts who take part in the chosen format (One host uses the lead only), each
 * read-only with Recast… behind a confirmation (research R8), and Invite a guest… for one
 * episode (011 FR-020). */
export default function SeriesHosts(props: SeriesHostsProps) {
  const [recasting, setRecasting] = useState<HostSlot | null>(null)
  const [inviting, setInviting] = useState<HostSlot | null>(null)
  const present = props.hosts.slice(0, props.hostCount)
  const { guest, format } = props
  return (
    <section aria-label="Hosts" style={{ display: 'grid', gap: 'var(--space-2)' }}>
      {present.map((host) => (
        <SeriesChair key={host.slot} host={host} guest={guest} personalities={props.personalities} onPlaySample={() => props.onPlaySample(host)}
          onRecast={() => setRecasting(host.slot)} onInvite={guest && format ? () => setInviting(host.slot) : undefined} />
      ))}
      <Recasting {...props} slot={recasting} onDone={() => setRecasting(null)} />
      <Inviting {...props} present={present} slot={inviting} onDone={() => setInviting(null)} />
    </section>
  )
}

function Inviting({ present, guest, format, personalities, slot, onDone }: SeriesHostsProps & { present: SeriesHostView[]; slot: HostSlot | null; onDone: () => void }) {
  const host = present.find((h) => h.slot === slot)
  if (!host || !guest || !format) return null
  const invite = (personalityId: string | null) => {
    onDone()
    void guest.cast(host.slot, format, personalityId)
  }
  return <GuestDialog host={host} otherHost={present.find((h) => h.slot !== host.slot)} personalities={personalities} onInvite={invite} onCancel={onDone} />
}

interface ChairProps {
  host: SeriesHostView
  guest: GuestControls | undefined
  personalities: PersonalityOption[]
  onPlaySample: () => void
  onRecast: () => void
  onInvite: (() => void) | undefined
}

/** One chair: its regular host, or today's guest with the regular host away. The never-heard
 * second host of a One host series is not away: the show's expert just joins (FR-024a). */
function SeriesChair({ host, guest, personalities, onPlaySample, onRecast, onInvite }: ChairProps) {
  if (guest?.seatSlot !== host.slot) return <SeriesHostCard host={host} onPlaySample={onPlaySample} onRecast={onRecast} onInvite={onInvite} />
  const seat = <GuestSeat guest={guest} personalities={personalities} />
  if (host.has_taken_part === false) return seat
  return (
    <>
      <SeriesHostCard host={host} onPlaySample={onPlaySample} isAway />
      {seat}
    </>
  )
}

function GuestSeat({ guest, personalities }: { guest: GuestControls; personalities: PersonalityOption[] }) {
  const label = personalities.find((p) => p.personality_id === guest.guest?.personality_id)?.label ?? ''
  return <GuestCard guest={guest.guest} personalityLabel={label} isCasting={guest.isCasting} error={guest.error}
    onAnother={() => void guest.another()} onRemove={guest.isAutomatic ? undefined : guest.remove} />
}

function Recasting({ hosts, personalities, keepsVoice, series, slot, onDone }: SeriesHostsProps & { slot: HostSlot | null; onDone: () => void }) {
  const controls = useRecast(series.seriesId, series.language, series.learnerName)
  const host = hosts.find((candidate) => candidate.slot === slot)
  if (!host) return null
  const confirm = async (personalityId: string | null) => {
    await controls.recast(host.slot, personalityId)
    onDone()
  }
  return <RecastDialog host={host} otherHost={hosts.find((other) => other.slot !== host.slot)} personalities={personalities}
    keepsVoice={keepsVoice} isBusy={controls.isRecasting} error={controls.error} onConfirm={(id) => void confirm(id)} onCancel={onDone} />
}
