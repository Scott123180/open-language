import type { PodcastCatalog, ShowDraft } from '../../services/podcastsApi'
import { useShowDiscovery } from '../../hooks/podcasts/useShowDiscovery'
import ErrorBanner from '../shared/ErrorBanner'
import ShowCard from './ShowCard'
import { mutedTextStyle, secondaryButtonStyle } from './styles'

interface FindNewShowProps {
  catalog: PodcastCatalog
  onChoose: (show: ShowDraft) => void
  onToggleFavourite: (show: ShowDraft) => void
}

const listStyle = {
  listStyle: 'none',
  margin: 0,
  padding: 0,
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 280px), 1fr))',
  gap: 'var(--space-4)',
}

/** Fresh shows on request; the ready-made list never changes (FR-016, FR-015). */
export default function FindNewShow({ catalog, onChoose, onToggleFavourite }: FindNewShowProps) {
  const discovery = useShowDiscovery()
  return (
    <section aria-labelledby="find-new-show-heading" style={{ display: 'grid', gap: 'var(--space-3)' }}>
      <h2 id="find-new-show-heading" style={{ margin: 0, fontSize: 'var(--text-lg)', color: 'var(--color-text)' }}>Something new</h2>
      <button type="button" onClick={() => void discovery.find()} disabled={discovery.isFinding} style={{ ...secondaryButtonStyle, justifySelf: 'start' }}>
        {discovery.suggestions.length > 0 ? 'Show me others' : 'Find a new show'}
      </button>
      {discovery.error && <ErrorBanner message={discovery.error} />}
      <div aria-live="polite" style={{ display: 'grid', gap: 'var(--space-3)' }}>
        {discovery.isFinding && <p style={{ ...mutedTextStyle, margin: 0 }}>Finding new shows…</p>}
        <SuggestionList suggestions={discovery.suggestions} catalog={catalog} onChoose={onChoose} onToggleFavourite={onToggleFavourite} />
      </div>
    </section>
  )
}

function SuggestionList({ suggestions, catalog, onChoose, onToggleFavourite }: FindNewShowProps & { suggestions: ShowDraft[] }) {
  if (suggestions.length === 0) return null
  const isFavourite = (show: ShowDraft) => catalog.my_shows.some((mine) => mine.title === show.title && mine.is_favourite)
  return (
    <ul style={listStyle}>
      {suggestions.map((show) => (
        <li key={show.title} style={{ display: 'flex' }}>
          <ShowCard show={{ ...show, is_favourite: isFavourite(show) }} personalities={catalog.personalities}
            onChoose={() => onChoose(show)} onToggleFavourite={() => onToggleFavourite({ ...show, is_favourite: isFavourite(show) } as ShowDraft)} />
        </li>
      ))}
    </ul>
  )
}
