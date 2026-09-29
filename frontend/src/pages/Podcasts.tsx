import { useLocation, useNavigate } from 'react-router-dom'
import ErrorBanner from '../components/shared/ErrorBanner'
import PageShell from '../components/podcasts/PageShell'
import PlainNotice from '../components/podcasts/PlainNotice'
import ShowList from '../components/podcasts/ShowList'
import { usePodcastCatalog } from '../hooks/podcasts/usePodcastCatalog'

/** The Podcasts screen: choosing a show is its one primary action (FR-001, FR-002). */
export default function Podcasts() {
  const navigate = useNavigate()
  const notice = (useLocation().state as { message?: string } | null)?.message
  const { catalog, error } = usePodcastCatalog()
  return (
    <PageShell title="Podcasts" backTo="/" backLabel="Back to Home">
      <PlainNotice message={notice} />
      {error && <ErrorBanner message={error} />}
      {!catalog && !error && <p aria-live="polite">Loading shows…</p>}
      {catalog && <ShowList catalog={catalog} onChoose={(show) => navigate(`/podcasts/setup?show=${show.show_id}`)} />}
    </PageShell>
  )
}
