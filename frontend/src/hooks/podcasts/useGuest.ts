import { useEffect, useRef, useState } from 'react'
import * as podcasts from '../../services/podcastsApi'
import type { HostDraft, HostSlot, PodcastFormatId } from '../../services/podcastsApi'

interface Seat {
  slot: HostSlot
  format: PodcastFormatId
  personalityId: string | null
}

export interface GuestControls {
  guest: HostDraft | null
  isCasting: boolean
  error: string | null
  cast: (slot: HostSlot, format: PodcastFormatId, personalityId: string | null) => Promise<void>
  /** Another guest: the same seat and personality, never a name drawn before. */
  another: () => Promise<void>
  remove: () => void
}

/** A guest for one series episode, cast by the server and kept only on this screen until Start
 * (011 R10). Leaving the screen forgets them. */
export function useGuest(seriesId: number | null, language: string, learnerName: string): GuestControls {
  const [state, setState] = useState<GuestState>(NO_GUEST)
  const seat = useRef<Seat | null>(null)
  const drawn = useRef<string[]>([])
  const draw = async (next: Seat) => {
    seat.current = next
    setState((current) => ({ ...current, isCasting: true, error: null }))
    const cast = await castState(seriesId!, guestBody(next, language, learnerName, drawn.current))
    if (cast.guest) drawn.current = [...drawn.current, cast.guest.name]
    setState(cast)
  }
  const remove = () => {
    seat.current = null
    setState(NO_GUEST)
  }
  return { ...state, remove, cast: (slot, format, id) => draw({ slot, format, personalityId: id }), another: () => (seat.current ? draw(seat.current) : Promise.resolve()) }
}

interface GuestState {
  guest: HostDraft | null
  isCasting: boolean
  error: string | null
}

const NO_GUEST: GuestState = { guest: null, isCasting: false, error: null }

async function castState(seriesId: number, body: podcasts.GuestBody): Promise<GuestState> {
  try {
    return { ...NO_GUEST, guest: await podcasts.castGuest(seriesId, body) }
  } catch (failure) {
    return { ...NO_GUEST, error: failure instanceof Error ? failure.message : String(failure) }
  }
}

function guestBody(seat: Seat, language: string, learnerName: string, avoid: string[]): podcasts.GuestBody {
  return {
    language,
    slot: seat.slot,
    format: seat.format,
    personality_id: seat.personalityId,
    learner_name: learnerName.trim() || null,
    avoid_names: avoid,
  }
}

interface ExpertSeat {
  /** A One host series turned two-host for this episode only. */
  isWanted: boolean
  format: PodcastFormatId
  expertId: string | null
}

/** The show's expert takes the second chair while a One host series is Panel or Listen for
 * this episode, and leaves when the format goes back (011 FR-024a). */
export function useExpertGuest(controls: GuestControls, { isWanted, format, expertId }: ExpertSeat): void {
  const { guest, isCasting, error, cast, remove } = controls
  useEffect(() => {
    if (isWanted && !guest && !isCasting && !error) void cast('second', format, expertId)
    if (!isWanted && guest?.slot === 'second') remove()
    // eslint-disable-next-line react-hooks/exhaustive-deps -- cast and remove are new each render
  }, [isWanted, guest, isCasting, error, format, expertId])
}
