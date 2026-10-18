import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import * as podcasts from '../../services/podcastsApi'
import type { PodcastCatalog, ShowDraft, ShowListing } from '../../services/podcastsApi'
import { PODCAST_CATALOG_KEY } from './usePodcastCatalog'

export const FAVOURITE_FAILED = "That favourite couldn't be saved. Please try again."

/** A show a list can favourite: a listing, or an unsaved suggestion with no state yet. */
export type FavouriteShow = ShowDraft & { is_favourite?: boolean }

const isSameShow = (a: FavouriteShow, b: FavouriteShow) =>
  (a.show_id !== null && a.show_id === b.show_id) ||
  (a.saved_show_id != null && a.saved_show_id === b.saved_show_id) ||
  (a.title === b.title && a.source === b.source)

const marked = (shows: ShowListing[], show: FavouriteShow, isFavourite: boolean) =>
  shows.map((each) => (isSameShow(each, show) ? { ...each, is_favourite: isFavourite } : each))

/** Toggle a favourite at once, then save it; a failure puts it back and says so (Principle IV). */
export function useFavourite() {
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)
  const toggle = (show: FavouriteShow) => {
    const isFavourite = !show.is_favourite
    const before = queryClient.getQueryData<PodcastCatalog>(PODCAST_CATALOG_KEY)
    queryClient.setQueryData<PodcastCatalog>(PODCAST_CATALOG_KEY, (current) =>
      current && { ...current, shows: marked(current.shows, show, isFavourite), my_shows: marked(current.my_shows, show, isFavourite) })
    setError(null)
    podcasts.setFavourite(show, isFavourite).then(
      () => void queryClient.invalidateQueries({ queryKey: PODCAST_CATALOG_KEY }),
      () => { queryClient.setQueryData(PODCAST_CATALOG_KEY, before); setError(FAVOURITE_FAILED) },
    )
  }
  return { toggle, error }
}
