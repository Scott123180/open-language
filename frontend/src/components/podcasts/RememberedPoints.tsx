import { useState, type CSSProperties } from 'react'
import type { RememberedPoint, SeriesDetail } from '../../services/podcastsApi'
import ConfirmDialog from '../shared/ConfirmDialog'
import { mutedTextStyle, secondaryButtonStyle } from './styles'

interface RememberedPointsProps {
  detail: SeriesDetail
  onStartOver: () => void
  isStartingOver: boolean
}

const START_OVER_MESSAGE =
  'The hosts will forget every episode of this series and start again at episode 1. Your past episodes stay in Past Chats.'

/** What the hosts remember, exactly as they are given it, and Start over (FR-011). */
export default function RememberedPoints({ detail, onStartOver, isStartingOver }: RememberedPointsProps) {
  const [isOpen, setOpen] = useState(false)
  const [isConfirming, setConfirming] = useState(false)
  return (
    <section style={sectionStyle}>
      <button type="button" aria-expanded={isOpen} aria-controls="remembered-points" onClick={() => setOpen(!isOpen)} style={toggleStyle}>
        What the hosts remember
      </button>
      {isOpen && <PointLists detail={detail} onStartOver={() => setConfirming(true)} isStartingOver={isStartingOver} />}
      {isConfirming && (
        <ConfirmDialog title="Start over?" message={START_OVER_MESSAGE} confirmLabel="Start over" isDestructive
          onConfirm={() => { setConfirming(false); onStartOver() }} onCancel={() => setConfirming(false)} />
      )}
    </section>
  )
}

function PointLists({ detail, onStartOver, isStartingOver }: RememberedPointsProps) {
  const { topics, about_learner } = detail.remembered
  return (
    <div id="remembered-points" style={{ display: 'grid', gap: 'var(--space-3)' }}>
      {detail.memory_status === 'running' && <p role="status" style={{ ...mutedTextStyle, margin: 0 }}>Updating…</p>}
      <PointList heading="Topics covered" points={topics} />
      <PointList heading="About you" points={about_learner} />
      <button type="button" onClick={onStartOver} disabled={isStartingOver} style={{ ...secondaryButtonStyle, alignSelf: 'flex-start' }}>Start over…</button>
    </div>
  )
}

function PointList({ heading, points }: { heading: string; points: RememberedPoint[] }) {
  return (
    <div>
      <h3 style={headingStyle}>{heading}</h3>
      {points.length === 0 ? <p style={{ ...mutedTextStyle, margin: 0 }}>Nothing yet.</p> : (
        <ul style={listStyle}>
          {points.map((point) => (
            <li key={point.point_id} style={itemStyle}><span>{point.text}</span><span style={mutedTextStyle}>{`Episode ${point.episode_number}`}</span></li>
          ))}
        </ul>
      )}
    </div>
  )
}

const sectionStyle: CSSProperties = { display: 'grid', gap: 'var(--space-3)', padding: 'var(--space-4)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-lg)' }
const toggleStyle: CSSProperties = { ...secondaryButtonStyle, alignSelf: 'flex-start', justifySelf: 'start', fontWeight: 600 }
const headingStyle: CSSProperties = { margin: '0 0 var(--space-1)', fontSize: 'var(--text-sm)', color: 'var(--color-text)' }
const listStyle: CSSProperties = { listStyle: 'none', margin: 0, padding: 0, display: 'grid', gap: 'var(--space-1)' }
const itemStyle: CSSProperties = { display: 'flex', justifyContent: 'space-between', gap: 'var(--space-3)', color: 'var(--color-text)', lineHeight: 'var(--leading-relaxed)' }
