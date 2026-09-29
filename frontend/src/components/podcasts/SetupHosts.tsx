import type { PersonalityOption, ShowDraft } from '../../services/podcastsApi'
import HostCard from './HostCard'

interface SetupHostsProps {
  show: ShowDraft
  personalities: PersonalityOption[]
  hostCount: number
}

/** The hosts who take part in the chosen format: One host uses the lead only (FR-003). */
export default function SetupHosts({ show, personalities, hostCount }: SetupHostsProps) {
  const labelOf = (id: string) => personalities.find((p) => p.personality_id === id)?.label ?? id
  return (
    <section aria-label="Hosts" style={{ display: 'grid', gap: 'var(--space-2)' }}>
      {show.hosts.slice(0, hostCount).map((host) => (
        <HostCard key={host.slot} host={host} personalityLabel={labelOf(host.personality_id)} />
      ))}
    </section>
  )
}
