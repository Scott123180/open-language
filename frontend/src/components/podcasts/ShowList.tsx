import type { PodcastCatalog, ShowDraft } from '../../services/podcastsApi'
import ShowCard from './ShowCard'

interface ShowListProps {
  catalog: PodcastCatalog
  onChoose: (show: ShowDraft) => void
}

/** The ready-made shows, each a card whose choice is the screen's one primary action. */
export default function ShowList({ catalog, onChoose }: ShowListProps) {
  return (
    <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'grid', gap: 'var(--space-3)' }}>
      {catalog.shows.map((show) => (
        <li key={show.show_id ?? show.title}>
          <ShowCard show={show} personalities={catalog.personalities} onChoose={onChoose} />
        </li>
      ))}
    </ul>
  )
}
