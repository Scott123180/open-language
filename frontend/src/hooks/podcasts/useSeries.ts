import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import * as podcasts from '../../services/podcastsApi'
import type { SeriesDetail } from '../../services/podcastsApi'

export const seriesKey = (seriesId: number | null) => ['podcast-series', seriesId]
const UPDATING_POLL_MS = 2000

/** A series' hosts and memory for the setup screen. Opening it starts the hosts catching up on
 * the last episodes in the background, so a Start rarely has to wait (research R6). */
export function useSeries(seriesId: number | null): { detail: SeriesDetail | undefined } {
  const query = useQuery({
    queryKey: seriesKey(seriesId),
    queryFn: () => podcasts.getSeries(seriesId!),
    enabled: seriesId !== null,
    refetchInterval: (current) => (current.state.data?.memory_status === 'running' ? UPDATING_POLL_MS : false),
  })
  useEffect(() => {
    if (seriesId !== null) void podcasts.catchUpSeriesMemory(seriesId).catch(() => undefined)
  }, [seriesId])
  return { detail: query.data }
}
