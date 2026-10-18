import type { EpisodeKind } from '../../services/podcastsApi'
import ChoiceTile from './ChoiceTile'
import SeriesExperimentalNote from './SeriesExperimentalNote'
import { choiceGroupStyle, choiceLegendStyle } from './styles'

interface EpisodeKindFieldsetProps {
  nextEpisodeNumber: number
  value: EpisodeKind
  onChange: (kind: EpisodeKind) => void
}

const ONE_OFF_DETAIL = "A stand-alone episode. Shuffle the hosts freely; it doesn't count towards the series."

/** The next series episode, the default, or a quick one-off beside it (FR-002, research R4). */
export default function EpisodeKindFieldset({ nextEpisodeNumber, value, onChange }: EpisodeKindFieldsetProps) {
  const seriesDetail = nextEpisodeNumber === 1
    ? 'The first episode of a continuing show. The hosts will remember it.'
    : 'The same hosts carry on, and remember the earlier episodes.'
  return (
    <fieldset style={choiceGroupStyle}>
      <legend style={choiceLegendStyle}>Episode</legend>
      <ChoiceTile group="podcast-episode-kind" isChecked={value === 'series'} onChoose={() => onChange('series')}
        option={{ value: 'series', label: `Episode ${nextEpisodeNumber}`, detail: seriesDetail }} />
      <ChoiceTile group="podcast-episode-kind" isChecked={value === 'one_off'} onChoose={() => onChange('one_off')}
        option={{ value: 'one_off', label: 'One-off episode', detail: ONE_OFF_DETAIL }} />
      {value === 'series' && <SeriesExperimentalNote />}
    </fieldset>
  )
}
