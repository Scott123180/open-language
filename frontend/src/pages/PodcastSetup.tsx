import ErrorBanner from '../components/shared/ErrorBanner'
import PageShell from '../components/podcasts/PageShell'
import SetupForm from '../components/podcasts/SetupForm'
import { usePodcastCatalog } from '../hooks/podcasts/usePodcastCatalog'
import { usePodcastPreferences } from '../hooks/podcasts/usePodcastPreferences'
import { useSetupForm } from '../hooks/podcasts/useSetupForm'
import { useSetupShow } from '../hooks/podcasts/useSetupShow'
import { useStartEpisode } from '../hooks/podcasts/useStartEpisode'

/** The setup screen: the show, its hosts, format, length and name, then Start episode. */
export default function PodcastSetup() {
  const { catalog, error } = usePodcastCatalog()
  const { preferences } = usePodcastPreferences()
  const show = useSetupShow(catalog)
  const form = useSetupForm(catalog, preferences)
  const starting = useStartEpisode()
  return (
    <PageShell title={show?.title ?? 'Set up your episode'} backTo="/podcasts" backLabel="Back to Podcasts">
      {error && <ErrorBanner message={error} />}
      {show && catalog ? <SetupForm show={show} catalog={catalog} form={form} starting={starting} /> : !error && <p aria-live="polite">Loading…</p>}
    </PageShell>
  )
}
