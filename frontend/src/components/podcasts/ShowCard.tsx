import { useId, type CSSProperties, type ReactNode } from 'react'
import type { PersonalityOption, SeriesSummary, ShowDraft } from '../../services/podcastsApi'
import { roleText } from './learnerRole'
import RoleBadge from './RoleBadge'
import FavouriteToggle from './FavouriteToggle'
import ShowCast from './ShowCast'
import { cardStyle, visuallyHiddenStyle } from './styles'

/** A show as a card shows it: a draft, with its series once it has one (010). */
type CardShow = ShowDraft & { series?: SeriesSummary | null; is_favourite?: boolean }

interface ShowCardProps {
  show: CardShow
  personalities: PersonalityOption[]
  onChoose: (show: CardShow) => void
  /** With it, the card is a group: the choose button, then the favourite toggle (010 US4). */
  onToggleFavourite?: (show: CardShow) => void
  /** Another secondary action beside the toggle, such as Remove. */
  extraAction?: ReactNode
}

const showCardStyle: CSSProperties = { ...cardStyle, gap: 'var(--space-4)', height: '100%', padding: 'var(--space-5)' }

const topicStyle: CSSProperties = {
  fontSize: 'var(--text-xs)',
  fontWeight: 'var(--weight-semibold)' as CSSProperties['fontWeight'],
  letterSpacing: '0.08em',
  textTransform: 'uppercase',
  color: 'var(--color-text-muted)',
}

const footerStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 'var(--space-2)',
  marginTop: 'auto',
  paddingTop: 'var(--space-3)',
  borderTop: '1px solid var(--color-border-subtle)',
}

const groupStyle: CSSProperties = { display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', width: '100%' }
const actionsStyle: CSSProperties = { display: 'flex', justifyContent: 'flex-end', gap: 'var(--space-2)' }

const seriesBadgeStyle: CSSProperties = {
  fontSize: 'var(--text-sm)',
  fontWeight: 'var(--weight-semibold)' as CSSProperties['fontWeight'],
  color: 'var(--color-primary-text)',
  background: 'var(--color-primary-subtle)',
  borderRadius: 'var(--radius-full)',
  padding: '2px var(--space-3)',
}

/** "Episode 2 next" or "Episode 1 unfinished"; null for a show with no series yet. */
function seriesText(series: SeriesSummary | null | undefined): string | null {
  if (!series) return null
  const unfinished = series.unfinished_episode
  return unfinished ? `Episode ${unfinished.episode_number} unfinished` : `Episode ${series.next_episode_number} next`
}

/** "Topic: food. Lucía (Enthusiast) & Marco (Dry sceptic). You're the guest. Episode 2 next." */
function describeShow(show: CardShow, labelOf: (id: string) => string): string {
  const hosts = show.hosts.map((host) => `${host.name} (${labelOf(host.personality_id)})`).join(' & ')
  const series = seriesText(show.series)
  return `Topic: ${show.topic}. ${hosts}. ${roleText(show.learner_role)}.${series ? ` ${series}.` : ''}`
}

/** A show card. With a favourite toggle it is a group, the toggle beside the choose button and
 * never inside it, so each is its own control. */
export default function ShowCard(props: ShowCardProps) {
  if (!props.onToggleFavourite) return <ShowCardButton {...props} />
  const { show, onToggleFavourite, extraAction } = props
  return (
    <div role="group" aria-label={show.title} style={groupStyle}>
      <ShowCardButton {...props} />
      <div style={actionsStyle}>
        <FavouriteToggle title={show.title} isFavourite={show.is_favourite ?? false} onToggle={() => onToggleFavourite(show)} />
        {extraAction}
      </div>
    </div>
  )
}

/** One show: a button named by its title. The topic sits over the title, the hosts under it and
 * the learner's role at the foot; screen readers get the same as one sentence. */
function ShowCardButton({ show, personalities, onChoose }: ShowCardProps) {
  const labelOf = (id: string) => personalities.find((p) => p.personality_id === id)?.label ?? id
  const detailsId = `${useId()}-details`
  return (
    <button type="button" aria-label={show.title} aria-describedby={detailsId} onClick={() => onChoose(show)} style={showCardStyle}>
      <span id={detailsId} style={visuallyHiddenStyle}>{describeShow(show, labelOf)}</span>
      <span aria-hidden="true" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
        <span style={topicStyle}>{show.topic}</span>
        <span style={{ fontSize: 'var(--text-md)', fontWeight: 'var(--weight-semibold)' as never }}>{show.title}</span>
      </span>
      <span aria-hidden="true"><ShowCast hosts={show.hosts} labelOf={labelOf} /></span>
      <span aria-hidden="true" style={footerStyle}>
        <RoleBadge role={show.learner_role} />
        {seriesText(show.series) && <span style={seriesBadgeStyle}>{seriesText(show.series)}</span>}
      </span>
    </button>
  )
}
