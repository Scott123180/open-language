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

/** The episode header: back to Podcasts, the show and its hosts, and the level control. */
export default function EpisodeHeader({ episode }: { episode: Episode }) {
  const hostNames = episode.hosts.map((host) => host.name)
  return (
    <header style={headerStyle}>
      <Link to="/podcasts" className="back-link">Podcasts</Link>
      <div style={{ minWidth: 0 }}>
        <h1 style={{ margin: 0, fontSize: 'var(--text-md)', color: 'var(--color-text)' }}>{episode.show.title}</h1>
        <PodcastLabel formatLabel={episode.format_label} hostNames={hostNames} />
      </div>
      <ConversationLevelControl />
    </header>
  )
}
