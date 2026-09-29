import { useState } from 'react'
import * as podcasts from '../../services/podcastsApi'
import type { HostDraft, HostSlot, ShowDraft } from '../../services/podcastsApi'

export interface SetupHosts {
  hosts: HostDraft[]
  shufflingSlot: HostSlot | null
  error: string | null
  shuffle: (slot: HostSlot) => Promise<void>
  setPersonality: (slot: HostSlot, personalityId: string) => void
  playSample: (host: HostDraft) => void
}

const SHUFFLE_FAILED = 'That host could not be shuffled. Please try again.'
const withHost = (hosts: HostDraft[], next: HostDraft) => hosts.map((host) => (host.slot === next.slot ? next : host))

/** The show's hosts as the learner shapes them before starting (US5). Start uses these. */
export function useSetupHosts(show: ShowDraft, learnerName: string): SetupHosts {
  const [hosts, setHosts] = useState(show.hosts)
  const [shufflingSlot, setShufflingSlot] = useState<HostSlot | null>(null)
  const [error, setError] = useState<string | null>(null)
  const shuffle = async (slot: HostSlot) => {
    setShufflingSlot(slot)
    setError(null)
    const body = { language: show.language, slot, hosts, learner_name: learnerName.trim() || null }
    await podcasts.shuffleHost(body)
      .then((next) => setHosts((current) => withHost(current, next)))
      .catch((e: unknown) => setError(e instanceof Error ? e.message : SHUFFLE_FAILED))
    setShufflingSlot(null)
  }
  const setPersonality = (slot: HostSlot, personalityId: string) =>
    setHosts((current) => current.map((host) => (host.slot === slot ? { ...host, personality_id: personalityId } : host)))
  const playSample = (host: HostDraft) => void new Audio(podcasts.voiceSampleUrl(host.voice_key, host.name)).play().catch(() => undefined)
  return { hosts, shufflingSlot, error, shuffle, setPersonality, playSample }
}
