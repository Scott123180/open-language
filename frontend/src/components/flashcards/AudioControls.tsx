import type { CSSProperties, ReactNode } from 'react'
import { IconVolume, IconClock } from '../shared/icons'
import { useWordAudio } from './useWordAudio'

interface Props {
  ttsUrl: string
  onPlay?: (playbackRate: number) => void
}

const NORMAL_RATE = 1.0
const SLOW_RATE = 0.6

const rowStyle: CSSProperties = { display: 'flex', gap: '8px', justifyContent: 'center' }
const buttonStyle: CSSProperties = {
  padding: '8px 16px',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius)',
  background: 'var(--color-surface)',
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  gap: '6px',
}
const failureStyle: CSSProperties = {
  margin: '8px 0 0',
  textAlign: 'center',
  fontSize: '0.85rem',
  color: 'var(--color-text-muted)',
}

export default function AudioControls({ ttsUrl, onPlay }: Props) {
  const audio = useWordAudio(ttsUrl)
  const play = (rate: number) => (onPlay ? onPlay(rate) : void audio.play(rate))
  return (
    <div>
      <div style={rowStyle}>
        <AudioButton label="Listen" onClick={() => play(NORMAL_RATE)} isPrimary>
          <IconVolume size={14} /> Listen
        </AudioButton>
        <AudioButton label="Slow speed" onClick={() => play(SLOW_RATE)}>
          <IconClock size={14} /> Slow
        </AudioButton>
      </div>
      <AudioFailureMessage message={audio.failureMessage} />
    </div>
  )
}

interface AudioButtonProps {
  label: string
  onClick: () => void
  isPrimary?: boolean
  children: ReactNode
}

function AudioButton({ label, onClick, isPrimary = false, children }: AudioButtonProps) {
  const style: CSSProperties = {
    ...buttonStyle,
    color: isPrimary ? 'var(--color-text)' : 'var(--color-text-muted)',
    fontSize: isPrimary ? '0.9rem' : '0.85rem',
  }
  return (
    <button aria-label={label} onClick={onClick} style={style}>
      {children}
    </button>
  )
}

function AudioFailureMessage({ message }: { message: string | null }) {
  if (!message) return null
  return (
    <p role="status" style={failureStyle}>
      {message}
    </p>
  )
}
