import type { StartEpisode } from '../../hooks/podcasts/useStartEpisode'
import ErrorBanner from '../shared/ErrorBanner'
import PlainNotice from './PlainNotice'
import { primaryButtonStyle, secondaryButtonStyle } from './styles'

interface StartActionsProps {
  label: string
  starting: StartEpisode
  onStart: () => void
  hostNames: string[]
  /** The episode the hosts catch up on before the next one starts. */
  lastEpisode: number
}

const rowStyle = { display: 'flex', flexWrap: 'wrap' as const, gap: 'var(--space-2)' }

/** The setup screen's Start, and what it says while the hosts catch up (research R6). */
export default function StartActions({ label, starting, onStart, hostNames, lastEpisode }: StartActionsProps) {
  const { phase, detail } = starting.catchUp
  const hasFailed = phase === 'failed' || phase === 'timedOut'
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
      {phase === 'catchingUp' && <PlainNotice message={`${hostNames.join(' and ')} are catching up on episode ${lastEpisode}. This takes a few seconds.`} />}
      {hasFailed && <PlainNotice message={`The hosts couldn't catch up on episode ${lastEpisode}. ${detail}`} />}
      {starting.error && <ErrorBanner message={starting.error} />}
      {hasFailed ? <CatchUpChoices starting={starting} /> : (
        <button type="button" onClick={onStart} disabled={starting.isStarting} aria-busy={phase === 'catchingUp'} style={{ ...primaryButtonStyle, alignSelf: 'flex-start' }}>{label}</button>
      )}
    </div>
  )
}

function CatchUpChoices({ starting }: { starting: StartEpisode }) {
  return (
    <div style={rowStyle}>
      <button type="button" onClick={() => void starting.retry()} style={primaryButtonStyle}>Try again</button>
      <button type="button" onClick={() => void starting.startWithoutUpdate()} style={secondaryButtonStyle}>Start without it</button>
    </div>
  )
}
