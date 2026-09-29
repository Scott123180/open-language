import AudioPlayer from '../shared/AudioPlayer'
import type { PodcastEpisode } from '../../hooks/podcasts/usePodcastEpisode'
import type { Episode } from '../../services/podcastsApi'
import { useEpisodeAudio } from '../../hooks/podcasts/useEpisodeAudio'
import { useContinueFocus } from '../../hooks/podcasts/useContinueFocus'
import EpisodeHeader from './EpisodeHeader'
import HostVoiceNotices from './HostVoiceNotices'
import TurnBanner from './TurnBanner'
import EpisodeTranscript from './EpisodeTranscript'
import EpisodeError from './EpisodeError'
import EpisodeFooter from './EpisodeFooter'
import { lastSpeakerName } from './speakerName'

const layoutStyle = { display: 'flex', flexDirection: 'column' as const, height: '100vh', background: 'var(--color-bg)' }

/** A loaded episode: header, notices, whose turn it is, the lines, and the actions. */
export default function EpisodeView({ state, episode }: { state: PodcastEpisode; episode: Episode }) {
  const audio = useEpisodeAudio(state.lines, episode.hosts)
  const continueRef = useContinueFocus(state.lines.length, state.awaiting)
  return (
    <main style={layoutStyle}>
      <EpisodeHeader episode={episode} />
      <HostVoiceNotices hosts={episode.hosts} />
      <TurnBanner turn={state.turn} speakerName={lastSpeakerName(state.lines, episode.hosts)} />
      <EpisodeTranscript conversationId={episode.conversation_id} lines={state.lines} hosts={episode.hosts} notes={state.notes} audio={audio} />
      <EpisodeError message={state.error} onRetry={state.retry} />
      <EpisodeFooter state={state} continueRef={continueRef} />
      <AudioPlayer src={audio.source?.src ?? null} autoPlay playbackRate={audio.source?.rate ?? 1} onEnded={audio.stopped} />
    </main>
  )
}
