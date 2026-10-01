import VoiceUnavailableNotice from '../chat/VoiceUnavailableNotice'
import type { EpisodeHost } from '../../services/podcastsApi'

/** One plain note per host whose voice is missing. Their lines stay as text (FR-031). */
export default function HostVoiceNotices({ hosts }: { hosts: EpisodeHost[] }) {
  const messages = hosts.map((host) => host.voice_unavailable_message).filter((message): message is string => Boolean(message))
  return (
    <>
      {messages.map((message) => (
        <VoiceUnavailableNotice key={message} message={message} />
      ))}
    </>
  )
}
