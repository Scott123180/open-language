import type { EpisodeLengthId, EpisodeLengthOption } from '../../services/podcastsApi'
import ChoiceTile from './ChoiceTile'
import { choiceGroupStyle, choiceLegendStyle } from './styles'

interface LengthFieldsetProps {
  lengths: EpisodeLengthOption[]
  value: EpisodeLengthId
  onChange: (length: EpisodeLengthId) => void
}

/** The length tiles: about 10, 20 or 40 host lines (FR-019). */
export default function LengthFieldset({ lengths, value, onChange }: LengthFieldsetProps) {
  return (
    <fieldset style={choiceGroupStyle}>
      <legend style={choiceLegendStyle}>Length</legend>
      {lengths.map((length) => (
        <ChoiceTile key={length.length_id} group="podcast-length" isChecked={value === length.length_id}
          option={{ value: length.length_id, label: length.label, detail: `About ${length.target_host_lines} host lines` }}
          onChoose={() => onChange(length.length_id)} />
      ))}
    </fieldset>
  )
}
