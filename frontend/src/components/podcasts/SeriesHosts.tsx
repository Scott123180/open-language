import { useState } from 'react'
import type { HostSlot, PersonalityOption, SeriesHostView } from '../../services/podcastsApi'
import { useRecast } from '../../hooks/podcasts/useRecast'
import RecastDialog from './RecastDialog'
import SeriesHostCard from './SeriesHostCard'

interface SeriesHostsProps {
  hosts: SeriesHostView[]
  hostCount: number
  personalities: PersonalityOption[]
  keepsVoice: boolean
  series: { seriesId: number; language: string; learnerName: string }
  onPlaySample: (host: SeriesHostView) => void
}

/** The series' hosts who take part in the chosen format (One host uses the lead only), each
 * read-only with Recast… behind a confirmation (research R8). */
export default function SeriesHosts({ hosts, hostCount, personalities, keepsVoice, series, onPlaySample }: SeriesHostsProps) {
  const [recasting, setRecasting] = useState<HostSlot | null>(null)
  const controls = useRecast(series.seriesId, series.language, series.learnerName)
  const host = hosts.find((candidate) => candidate.slot === recasting)
  const confirm = async (personalityId: string | null) => {
    await controls.recast(recasting!, personalityId)
    setRecasting(null)
  }
  return (
    <section aria-label="Hosts" style={{ display: 'grid', gap: 'var(--space-2)' }}>
      {hosts.slice(0, hostCount).map((each) => (
        <SeriesHostCard key={each.slot} host={each} onPlaySample={() => onPlaySample(each)} onRecast={() => setRecasting(each.slot)} />
      ))}
      {host && <RecastDialog host={host} otherHost={hosts.find((other) => other.slot !== host.slot)} personalities={personalities}
        keepsVoice={keepsVoice} isBusy={controls.isRecasting} error={controls.error} onConfirm={(id) => void confirm(id)} onCancel={() => setRecasting(null)} />}
    </section>
  )
}
