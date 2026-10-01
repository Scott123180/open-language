import type { EpisodeHost, EpisodeLine } from '../../services/podcastsApi'

/** The host who spoke last, named in the turn banner while the hosts have the floor. */
export function lastSpeakerName(lines: EpisodeLine[], hosts: EpisodeHost[]): string | null {
  const last = [...lines].reverse().find((line) => line.speaker === 'host')
  return hosts.find((host) => host.host_id === last?.host_id)?.name ?? null
}
