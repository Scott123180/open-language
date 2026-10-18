import type { SeriesDetail } from '../../services/podcastsApi'
import { useStartOver } from '../../hooks/podcasts/useStartOver'
import ErrorBanner from '../shared/ErrorBanner'
import RememberedPoints from './RememberedPoints'

/** What a series' hosts remember, with Start over, on the setup screen (FR-011). */
export default function SeriesMemoryPanel({ detail }: { detail: SeriesDetail }) {
  const { startOver, isStartingOver, error } = useStartOver(detail.series_id)
  return (
    <>
      <RememberedPoints detail={detail} onStartOver={startOver} isStartingOver={isStartingOver} />
      {error && <ErrorBanner message={error} />}
    </>
  )
}
