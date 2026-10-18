import type { SeriesHostView } from '../../services/podcastsApi'
import SeriesHostCard from './SeriesHostCard'

interface SeriesHostsProps {
  hosts: SeriesHostView[]
  hostCount: number
  onPlaySample: (host: SeriesHostView) => void
}

/** The series' hosts who take part in the chosen format: One host uses the lead only. */
export default function SeriesHosts({ hosts, hostCount, onPlaySample }: SeriesHostsProps) {
  return (
    <section aria-label="Hosts" style={{ display: 'grid', gap: 'var(--space-2)' }}>
      {hosts.slice(0, hostCount).map((host) => (
        <SeriesHostCard key={host.slot} host={host} onPlaySample={() => onPlaySample(host)} />
      ))}
    </section>
  )
}
