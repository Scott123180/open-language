import { useLocation, useNavigate } from 'react-router-dom'
import ErrorBanner from '../components/shared/ErrorBanner'
import PageShell from '../components/podcasts/PageShell'
import PlainNotice from '../components/podcasts/PlainNotice'
import FindNewShow from '../components/podcasts/FindNewShow'
import MyShows from '../components/podcasts/MyShows'
import NewShowSection from '../components/podcasts/NewShowSection'
import ShowList from '../components/podcasts/ShowList'
import { useFavourite } from '../hooks/podcasts/useFavourite'
import { usePodcastCatalog } from '../hooks/podcasts/usePodcastCatalog'
import type { ShowDraft } from '../services/podcastsApi'

/** Where choosing a show leads: a kept show of one's own by its saved id, else its template. */
const setupPath = (show: ShowDraft) =>
  show.saved_show_id != null ? `/podcasts/setup?saved=${show.saved_show_id}` : `/podcasts/setup?show=${show.show_id}`

/** The Podcasts screen: choosing a show is its one primary action (FR-001, FR-002); My shows
 * come first (010 FR-013); favourites and making one's own show are secondary. */
export default function Podcasts() {
  const navigate = useNavigate()
  const notice = (useLocation().state as { message?: string } | null)?.message
  const { catalog, error } = usePodcastCatalog()
  const favourite = useFavourite()
  const choose = (show: ShowDraft) => navigate(setupPath(show))
  const openSuggestion = (draft: ShowDraft) => navigate('/podcasts/setup', { state: { draft, idea: null, previousTitles: [] } })
  return (
    <PageShell title="Podcasts" backTo="/" backLabel="Back to Home" maxWidth="var(--width-grid)">
      <PlainNotice message={notice} />
      {(error ?? favourite.error) && <ErrorBanner message={(error ?? favourite.error)!} />}
      {!catalog && !error && <p aria-live="polite">Loading shows…</p>}
      {catalog && <MyShows catalog={catalog} onChoose={choose} onToggleFavourite={favourite.toggle} />}
      {catalog && <ShowList catalog={catalog} onChoose={choose} onToggleFavourite={favourite.toggle} />}
      {catalog && <FindNewShow catalog={catalog} onChoose={openSuggestion} onToggleFavourite={favourite.toggle} />}
      <NewShowSection />
    </PageShell>
  )
}
