import { useNavigate } from 'react-router-dom'
import type { SeriesSummary } from '../../services/podcastsApi'
import type { StartEpisode } from '../../hooks/podcasts/useStartEpisode'
import ContinueEpisode from './ContinueEpisode'
import StartActions from './StartActions'

interface SetupActionsProps {
  /** The show's series; null for a show with no series yet. */
  series: SeriesSummary | null
  isOneOff: boolean
  starting: StartEpisode
  onStart: () => void
  hostNames: string[]
}

/** Continue episode N when one is unfinished, otherwise Start episode N: never both (R4). */
export default function SetupActions({ series, isOneOff, starting, onStart, hostNames }: SetupActionsProps) {
  const navigate = useNavigate()
  const unfinished = isOneOff ? null : series?.unfinished_episode
  const isBusy = starting.isStarting || starting.catchUp.phase !== 'idle' || starting.error !== null
  if (unfinished && !isBusy) {
    const onContinue = (id: number) => navigate(`/podcasts/episodes/${id}`)
    return <ContinueEpisode unfinished={unfinished} onContinue={onContinue} onStartNew={onStart} isStarting={starting.isStarting} />
  }
  const label = isOneOff ? 'Start one-off episode' : `Start episode ${series?.next_episode_number ?? 1}`
  return <StartActions label={label} starting={starting} onStart={onStart} hostNames={hostNames} lastEpisode={series?.episode_count ?? 0} />
}
