import { useQuery } from '@tanstack/react-query'
import * as podcasts from '../../services/podcastsApi'
import type { PodcastCatalog } from '../../services/podcastsApi'

export const PODCAST_CATALOG_KEY = ['podcast-catalog']

/** Formats, lengths, personalities and ready-made shows for the current practice language. */
export function usePodcastCatalog(): { catalog: PodcastCatalog | undefined; error: string | null } {
  const query = useQuery({ queryKey: PODCAST_CATALOG_KEY, queryFn: podcasts.getPodcastCatalog })
  return { catalog: query.data, error: query.error ? query.error.message : null }
}
