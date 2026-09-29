import { useParams } from 'react-router-dom'
import ErrorBanner from '../components/shared/ErrorBanner'
import EpisodeView from '../components/podcasts/EpisodeView'
import { usePodcastEpisode } from '../hooks/podcasts/usePodcastEpisode'

/** An episode: Continue at the hosts' turn, Send at the learner's (contracts §13). */
export default function PodcastEpisode() {
  const conversationId = Number(useParams<{ conversationId: string }>().conversationId)
  const state = usePodcastEpisode(conversationId)
  if (state.episode) return <EpisodeView state={state} episode={state.episode} />
  return (
    <main style={{ padding: 'var(--space-8) var(--space-4)', background: 'var(--color-bg)', minHeight: '100vh' }}>
      {state.error ? <ErrorBanner message={state.error} /> : <p aria-live="polite">Loading the episode…</p>}
    </main>
  )
}
