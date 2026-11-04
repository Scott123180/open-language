import { useState } from 'react'
import type { HostSlot, PersonalityOption, SeriesHostView } from '../../services/podcastsApi'
import type { GuestControls } from '../../hooks/podcasts/useGuest'
import { useRecast } from '../../hooks/podcasts/useRecast'
import GuestCard from './GuestCard'
import RecastDialog from './RecastDialog'
import SeriesHostCard from './SeriesHostCard'

interface SeriesHostsProps {
  hosts: SeriesHostView[]
  hostCount: number
  personalities: PersonalityOption[]
  keepsVoice: boolean
  series: { seriesId: number; language: string; learnerName: string }
  /** 011: today's guest, who takes their chair for this episode only. */
  guest?: GuestControls
  onPlaySample: (host: SeriesHostView) => void
}

/** The series' hosts who take part in the chosen format (One host uses the lead only), each
 * read-only with Recast… behind a confirmation (research R8). */
export default function SeriesHosts({ hosts, hostCount, personalities, keepsVoice, series, guest, onPlaySample }: SeriesHostsProps) {
  const [recasting, setRecasting] = useState<HostSlot | null>(null)
  const controls = useRecast(series.seriesId, series.language, series.learnerName)
  const host = hosts.find((candidate) => candidate.slot === recasting)
  const confirm = async (personalityId: string | null) => {
    await controls.recast(recasting!, personalityId)
    setRecasting(null)
  }
  return (
    <section aria-label="Hosts" style={{ display: 'grid', gap: 'var(--space-2)' }}>
      {hosts.slice(0, hostCount).map((each) => (isGuestSeat(guest, each.slot)
        ? <GuestSeat key={each.slot} guest={guest!} personalities={personalities} />
        : <SeriesHostCard key={each.slot} host={each} onPlaySample={() => onPlaySample(each)} onRecast={() => setRecasting(each.slot)} />))}
      {host && <RecastDialog host={host} otherHost={hosts.find((other) => other.slot !== host.slot)} personalities={personalities}
        keepsVoice={keepsVoice} isBusy={controls.isRecasting} error={controls.error} onConfirm={(id) => void confirm(id)} onCancel={() => setRecasting(null)} />}
    </section>
  )
}

/** The chair a guest is in, or being cast for, this episode. */
function isGuestSeat(guest: GuestControls | undefined, slot: HostSlot): boolean {
  return guest !== undefined && (guest.guest?.slot === slot || (guest.isCasting && slot === 'second') || (guest.error !== null && slot === 'second'))
}

function GuestSeat({ guest, personalities }: { guest: GuestControls; personalities: PersonalityOption[] }) {
  const label = personalities.find((p) => p.personality_id === guest.guest?.personality_id)?.label ?? ''
  return <GuestCard guest={guest.guest} personalityLabel={label} isCasting={guest.isCasting} error={guest.error} onAnother={() => void guest.another()} />
}
