import type { PodcastCatalog, ShowDraft } from '../../services/podcastsApi'
import ShowCard from './ShowCard'

interface ShowListProps {
  catalog: PodcastCatalog
  onChoose: (show: ShowDraft) => void
  onToggleFavourite?: (show: ShowDraft) => void
}

/** As many columns as fit at 280px or more each: three on a wide screen, one on a phone. */
const listStyle = {
  listStyle: 'none',
  margin: 0,
  padding: 0,
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 280px), 1fr))',
  gap: 'var(--space-4)',
}

/** The ready-made shows, each a card whose choice is the screen's one primary action. */
export default function ShowList({ catalog, onChoose, onToggleFavourite }: ShowListProps) {
  return (
    <ul style={listStyle}>
      {catalog.shows.map((show) => (
        <li key={show.show_id ?? show.title} style={{ display: 'flex' }}>
          <ShowCard show={show} personalities={catalog.personalities} onChoose={onChoose} onToggleFavourite={onToggleFavourite} />
        </li>
      ))}
    </ul>
  )
}
