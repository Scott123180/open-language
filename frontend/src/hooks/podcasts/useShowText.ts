import type { EpisodeLine } from '../../services/podcastsApi'
import { usePodcastPreferences } from './usePodcastPreferences'

export interface ShowText {
  isOn: boolean
  change: (isOn: boolean) => void
  isHidden: (line: EpisodeLine) => boolean
}

/**
 * Listen hides a host line's words until it is tapped or Show text is on, and remembers the
 * switch (FR-043). A host without a voice is always shown: a hidden, silent line would be empty
 * (plan interpretation 5). One host and Panel always show every line.
 */
export function useShowText(isListening: boolean, canSpeak: (line: EpisodeLine) => boolean): ShowText {
  const { preferences, update } = usePodcastPreferences()
  const isOn = preferences?.is_show_text_on ?? false
  const isHidden = (line: EpisodeLine) =>
    isListening && !isOn && line.speaker === 'host' && !line.is_revealed && canSpeak(line)
  return { isOn, change: (next) => void update({ is_show_text_on: next }), isHidden }
}
