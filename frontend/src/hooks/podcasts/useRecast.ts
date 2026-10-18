import { useMutation, useQueryClient } from '@tanstack/react-query'
import * as podcasts from '../../services/podcastsApi'
import type { HostSlot } from '../../services/podcastsApi'
import { PODCAST_CATALOG_KEY } from './usePodcastCatalog'
import { seriesKey } from './useSeries'

interface RecastArgs {
  slot: HostSlot
  personalityId: string | null
}

export interface Recast {
  recast: (slot: HostSlot, personalityId: string | null) => Promise<void>
  isRecasting: boolean
  error: string | null
}

/** Recast one series host. The series shows the new host at once; the catalogue is reread so
 * the next Start sends the series' new hosts (research R8). */
export function useRecast(seriesId: number, language: string, learnerName: string): Recast {
  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationFn: ({ slot, personalityId }: RecastArgs) =>
      podcasts.recastHost(seriesId, slot, { language, learner_name: learnerName.trim() || null, personality_id: personalityId }),
    onSuccess: (detail) => {
      queryClient.setQueryData(seriesKey(seriesId), detail)
      void queryClient.invalidateQueries({ queryKey: PODCAST_CATALOG_KEY })
    },
  })
  const recast = (slot: HostSlot, personalityId: string | null) =>
    mutation.mutateAsync({ slot, personalityId }).then(() => undefined, () => undefined)
  return { recast, isRecasting: mutation.isPending, error: mutation.error?.message ?? null }
}
