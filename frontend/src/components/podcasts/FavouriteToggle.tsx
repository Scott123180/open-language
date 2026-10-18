import { secondaryButtonStyle } from './styles'

interface FavouriteToggleProps {
  title: string
  isFavourite: boolean
  onToggle: () => void
}

const toggleStyle = { ...secondaryButtonStyle, padding: '0 var(--space-3)', fontSize: 'var(--text-md)' }

/** A show's favourite mark: its own button beside the card, announced as pressed or not. */
export default function FavouriteToggle({ title, isFavourite, onToggle }: FavouriteToggleProps) {
  return (
    <button type="button" aria-pressed={isFavourite} aria-label={`Favourite ${title}`} onClick={onToggle}
      style={{ ...toggleStyle, color: isFavourite ? 'var(--color-primary-text)' : 'var(--color-text-muted)' }}>
      <span aria-hidden="true">{isFavourite ? '★' : '☆'}</span>
    </button>
  )
}
