import type { PodcastCatalog, ShowDraft, ShowListing } from '../../services/podcastsApi'
import RemoveShowButton from './RemoveShowButton'
import ShowCard from './ShowCard'

interface MyShowsProps {
  catalog: PodcastCatalog
  onChoose: (show: ShowDraft) => void
  onToggleFavourite: (show: ShowDraft) => void
}

/** Every My shows entry names its next episode; a show with no series yet starts at 1 (FR-013). */
const FIRST_EPISODE_TEXT = 'Episode 1 next'

const listStyle = {
  listStyle: 'none',
  margin: 0,
  padding: 0,
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 280px), 1fr))',
  gap: 'var(--space-4)',
}

/** Favourites, series in progress and played shows of one's own, first; hidden when empty. */
export default function MyShows({ catalog, onChoose, onToggleFavourite }: MyShowsProps) {
  if (catalog.my_shows.length === 0) return null
  return (
    <section aria-labelledby="my-shows-heading" style={{ display: 'grid', gap: 'var(--space-3)' }}>
      <h2 id="my-shows-heading" style={{ margin: 0, fontSize: 'var(--text-lg)', color: 'var(--color-text)' }}>My shows</h2>
      <ul style={listStyle}>
        {catalog.my_shows.map((show) => (
          <li key={showKey(show)} style={{ display: 'flex' }}>
            <ShowCard show={show} personalities={catalog.personalities} onChoose={onChoose} onToggleFavourite={onToggleFavourite} noSeriesText={FIRST_EPISODE_TEXT}
              extraAction={show.saved_show_id !== null ? <RemoveShowButton title={show.title} savedShowId={show.saved_show_id} /> : null} />
          </li>
        ))}
      </ul>
    </section>
  )
}

const showKey = (show: ShowListing) => show.show_id ?? `saved-${show.saved_show_id}`
