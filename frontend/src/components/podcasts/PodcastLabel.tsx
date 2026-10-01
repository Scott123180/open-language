import { mutedTextStyle } from './styles'

interface PodcastLabelProps {
  formatLabel: string
  hostNames: string[]
}

function podcastLabelText(formatLabel: string, hostNames: string[]): string {
  return `Podcast · ${formatLabel} · ${hostNames.join(' & ')}`
}

/** "Podcast · Panel · Lucía & Marco", for Past Chats and the episode header. */
export default function PodcastLabel({ formatLabel, hostNames }: PodcastLabelProps) {
  return <span style={mutedTextStyle}>{podcastLabelText(formatLabel, hostNames)}</span>
}
