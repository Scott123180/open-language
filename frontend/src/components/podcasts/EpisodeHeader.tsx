import { Link } from 'react-router-dom'
import ConversationLevelControl from '../chat/ConversationLevelControl'
import type { Episode } from '../../services/podcastsApi'
import PodcastLabel from './PodcastLabel'

const headerStyle = {
  display: 'grid',
  gridTemplateColumns: 'auto minmax(0, 1fr) auto',
  alignItems: 'center',
  gap: 'var(--space-3)',
  padding: 'var(--space-2) var(--space-4)',
  borderBottom: '1px solid var(--color-border)',
  background: 'var(--color-surface)',
}

/** "Big Little Questions · Episode 2" or "· One-off"; the title alone when the server says
 * nothing of series (010 contracts §2). */
function episodeTitle(episode: Episode): string {
  if (episode.series === undefined) return episode.show.title
  const kind = episode.series ? `Episode ${episode.series.episode_number}` : 'One-off'
  return `${episode.show.title} · ${kind}`
}

/** The episode header: back to Podcasts, the show and its hosts, and the level control. */
export default function EpisodeHeader({ episode }: { episode: Episode }) {
  const hostNames = episode.hosts.map((host) => host.name)
  return (
    <header style={headerStyle}>
      <Link to="/podcasts" className="back-link">Podcasts</Link>
      <div style={{ minWidth: 0 }}>
        <h1 style={{ margin: 0, fontSize: 'var(--text-md)', color: 'var(--color-text)' }}>{episodeTitle(episode)}</h1>
        <PodcastLabel formatLabel={episode.format_label} hostNames={hostNames} />
      </div>
      <ConversationLevelControl />
    </header>
  )
}
