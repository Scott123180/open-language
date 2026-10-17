import type { CSSProperties } from 'react'
import type { PersonalityOption, ShowDraft } from '../../services/podcastsApi'
import { roleText } from './learnerRole'
import RoleBadge from './RoleBadge'
import ShowCast from './ShowCast'
import { cardStyle, visuallyHiddenStyle } from './styles'

interface ShowCardProps {
  show: ShowDraft
  personalities: PersonalityOption[]
  onChoose: (show: ShowDraft) => void
}

const showCardStyle: CSSProperties = { ...cardStyle, gap: 'var(--space-4)', height: '100%', padding: 'var(--space-5)' }

const topicStyle: CSSProperties = {
  fontSize: 'var(--text-xs)',
  fontWeight: 'var(--weight-semibold)' as CSSProperties['fontWeight'],
  letterSpacing: '0.08em',
  textTransform: 'uppercase',
  color: 'var(--color-text-muted)',
}

const footerStyle: CSSProperties = { marginTop: 'auto', paddingTop: 'var(--space-3)', borderTop: '1px solid var(--color-border-subtle)' }

/** "Topic: food. Lucía (Enthusiast) & Marco (Dry sceptic). You're the guest." */
function describeShow(show: ShowDraft, labelOf: (id: string) => string): string {
  const hosts = show.hosts.map((host) => `${host.name} (${labelOf(host.personality_id)})`).join(' & ')
  return `Topic: ${show.topic}. ${hosts}. ${roleText(show.learner_role)}.`
}

/** One ready-made show: a button named by its title. The topic sits over the title, the hosts
 * under it and the learner's role at the foot; screen readers get the same as one sentence. */
export default function ShowCard({ show, personalities, onChoose }: ShowCardProps) {
  const labelOf = (id: string) => personalities.find((p) => p.personality_id === id)?.label ?? id
  const detailsId = `show-${show.show_id ?? show.title}-details`
  return (
    <button type="button" aria-label={show.title} aria-describedby={detailsId} onClick={() => onChoose(show)} style={showCardStyle}>
      <span id={detailsId} style={visuallyHiddenStyle}>{describeShow(show, labelOf)}</span>
      <span aria-hidden="true" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
        <span style={topicStyle}>{show.topic}</span>
        <span style={{ fontSize: 'var(--text-md)', fontWeight: 'var(--weight-semibold)' as never }}>{show.title}</span>
      </span>
      <span aria-hidden="true"><ShowCast hosts={show.hosts} labelOf={labelOf} /></span>
      <span aria-hidden="true" style={footerStyle}><RoleBadge role={show.learner_role} /></span>
    </button>
  )
}
