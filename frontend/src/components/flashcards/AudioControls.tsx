import { IconVolume, IconClock } from '../shared/icons'

interface Props {
  ttsUrl: string
  onPlay?: (playbackRate: number) => void
}

export default function AudioControls({ ttsUrl, onPlay }: Props) {
  function play(rate: number) {
    if (onPlay) {
      onPlay(rate)
      return
    }
    const audio = new Audio(ttsUrl)
    audio.playbackRate = rate
    audio.play().catch(() => {})
  }

  return (
    <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
      <button
        aria-label="Listen"
        onClick={() => play(1.0)}
        style={{
          padding: '8px 16px',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius)',
          background: 'var(--color-surface)',
          color: 'var(--color-text)',
          cursor: 'pointer',
          fontSize: '0.9rem',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
        }}
      >
        <IconVolume size={14} /> Listen
      </button>
      <button
        aria-label="Slow speed"
        onClick={() => play(0.6)}
        style={{
          padding: '8px 16px',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius)',
          background: 'var(--color-surface)',
          color: 'var(--color-text-muted)',
          cursor: 'pointer',
          fontSize: '0.85rem',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
        }}
      >
        <IconClock size={14} /> Slow
      </button>
    </div>
  )
}
