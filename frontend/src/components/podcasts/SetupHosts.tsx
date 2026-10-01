import type { PersonalityOption } from '../../services/podcastsApi'
import type { SetupHosts as SetupHostsState } from '../../hooks/podcasts/useSetupHosts'
import ErrorBanner from '../shared/ErrorBanner'
import HostCard from './HostCard'

interface SetupHostsProps {
  controls: SetupHostsState
  personalities: PersonalityOption[]
  hostCount: number
}

/** The hosts who take part in the chosen format: One host uses the lead only (FR-003). Two
 * hosts never share a personality, so each choice leaves out the other host's. */
export default function SetupHosts({ controls, personalities, hostCount }: SetupHostsProps) {
  const shown = controls.hosts.slice(0, hostCount)
  const otherOf = (slot: string) => shown.find((host) => host.slot !== slot)?.personality_id ?? null
  return (
    <section aria-label="Hosts" style={{ display: 'grid', gap: 'var(--space-2)' }}>
      {shown.map((host) => (
        <HostCard key={host.slot} host={host} personalities={personalities} otherPersonalityId={otherOf(host.slot)}
          isShuffling={controls.shufflingSlot === host.slot} onShuffle={() => void controls.shuffle(host.slot)}
          onPersonalityChange={(id) => controls.setPersonality(host.slot, id)} onPlaySample={() => controls.playSample(host)} />
      ))}
      {controls.error && <ErrorBanner message={controls.error} />}
    </section>
  )
}
