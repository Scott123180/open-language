import { useMutation, useQueryClient } from '@tanstack/react-query'
import * as podcasts from '../../services/podcastsApi'
import { PODCAST_CATALOG_KEY } from './usePodcastCatalog'
import { seriesKey } from './useSeries'

/** Start a series over; the catalogue is reread, so the show offers episode 1 again. */
export function useStartOver(seriesId: number) {
  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationFn: () => podcasts.resetSeries(seriesId),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: seriesKey(seriesId) })
      void queryClient.invalidateQueries({ queryKey: PODCAST_CATALOG_KEY })
    },
  })
  return { startOver: () => mutation.mutate(), isStartingOver: mutation.isPending, error: mutation.error?.message ?? null }
}
