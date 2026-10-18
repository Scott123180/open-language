import { useMutation, useQueryClient } from '@tanstack/react-query'
import * as podcasts from '../../services/podcastsApi'
import { PODCAST_CATALOG_KEY } from './usePodcastCatalog'

/** Remove a kept learner-made show; the catalogue is reread so it leaves My shows (FR-024). */
export function useRemoveShow() {
  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationFn: (savedShowId: number) => podcasts.removeShow(savedShowId),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: PODCAST_CATALOG_KEY }),
  })
  return { remove: (savedShowId: number) => mutation.mutate(savedShowId), isRemoving: mutation.isPending, error: mutation.error?.message ?? null }
}
