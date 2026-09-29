import type { CatalogVoices } from '../../services/podcastsApi'
import PlainNotice from './PlainNotice'

interface SetupVoiceNoticeProps {
  voices: CatalogVoices
  hostCount: number
}

/** Said before starting: no voice at all, or two hosts about to share one (spec edge case). */
export default function SetupVoiceNotice({ voices, hostCount }: SetupVoiceNoticeProps) {
  if (voices.unavailable_message) return <PlainNotice message={voices.unavailable_message} />
  return <PlainNotice message={hostCount > 1 ? voices.shared_voice_notice : null} />
}
