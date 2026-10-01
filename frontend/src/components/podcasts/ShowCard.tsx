import type { PersonalityOption, ShowDraft } from '../../services/podcastsApi'
import { cardStyle, mutedTextStyle } from './styles'

const ROLE_TEXT: Record<string, string> = {
  guest: "You're the guest",
  co_host: "You're a co-host",
  caller: "You're a caller",
}

interface ShowCardProps {
  show: ShowDraft
  personalities: PersonalityOption[]
  onChoose: (show: ShowDraft) => void
}

function hostSummary(show: ShowDraft, personalities: PersonalityOption[]): string {
  const labelOf = (id: string) => personalities.find((p) => p.personality_id === id)?.label ?? id
  return show.hosts.map((host) => `${host.name} (${labelOf(host.personality_id)})`).join(' & ')
}

/** One ready-made show: a button named by its title, described by topic, hosts and role. */
export default function ShowCard({ show, personalities, onChoose }: ShowCardProps) {
  const detailsId = `show-${show.show_id ?? show.title}-details`
  return (
    <button type="button" aria-label={show.title} aria-describedby={detailsId} onClick={() => onChoose(show)} style={cardStyle}>
      <span style={{ fontWeight: 'var(--weight-semibold)' as never }}>{show.title}</span>
      <span id={detailsId} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
        <span style={mutedTextStyle}>Topic: {show.topic}</span>
        <span style={mutedTextStyle}>{hostSummary(show, personalities)}</span>
        <span style={mutedTextStyle}>{ROLE_TEXT[show.learner_role] ?? show.learner_role}</span>
      </span>
    </button>
  )
}
