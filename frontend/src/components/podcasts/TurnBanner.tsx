import type { Turn } from '../../services/podcastsApi'
import { mutedTextStyle } from './styles'

interface TurnBannerProps {
  turn: Turn
  speakerName: string | null
}

function bannerText(turn: Turn, speakerName: string | null): string {
  if (turn === 'learner') return 'Your turn'
  if (turn === 'finished') return 'Episode finished'
  return speakerName ? `${speakerName} is speaking` : 'The hosts are speaking'
}

/** Whose turn it is, announced to screen readers as it changes. */
export default function TurnBanner({ turn, speakerName }: TurnBannerProps) {
  return (
    <p role="status" style={{ ...mutedTextStyle, margin: 0, padding: 'var(--space-2) var(--space-4)', color: 'var(--color-text)' }}>
      {bannerText(turn, speakerName)}
    </p>
  )
}
