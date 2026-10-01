import { Link } from 'react-router-dom'
import type { EpisodeSummaryRow } from '../../services/podcastsApi'
import PodcastLabel from './PodcastLabel'

/** A Past Chats row's podcast label and its way back into the episode (FR-032). */
export default function EpisodeRowLink({ row }: { row: EpisodeSummaryRow | undefined }) {
  if (!row) return null
  return (
    <span style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)', padding: '0 var(--space-4) var(--space-3)' }}>
      <PodcastLabel formatLabel={row.format_label} hostNames={row.host_names} />
      <Link to={`/podcasts/episodes/${row.conversation_id}`} style={{ color: 'var(--color-text)', fontSize: 'var(--text-sm)' }}>
        Continue episode
      </Link>
    </span>
  )
}
