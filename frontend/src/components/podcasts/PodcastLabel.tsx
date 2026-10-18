import { mutedTextStyle } from './styles'

interface PodcastLabelProps {
  formatLabel: string
  hostNames: string[]
  /** A series episode's number; none for a one-off or an episode from before series (010). */
  episodeNumber?: number | null
}

function podcastLabelText({ formatLabel, hostNames, episodeNumber }: PodcastLabelProps): string {
  const label = `Podcast · ${formatLabel} · ${hostNames.join(' & ')}`
  return episodeNumber ? `${label} · Episode ${episodeNumber}` : label
}

/** "Podcast · Panel · Lucía & Marco", for Past Chats and the episode header. */
export default function PodcastLabel(props: PodcastLabelProps) {
  return <span style={mutedTextStyle}>{podcastLabelText(props)}</span>
}
