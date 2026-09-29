import type { EpisodeLengthId, EpisodeLengthOption } from '../../services/podcastsApi'
import { fieldsetStyle, legendStyle, mutedTextStyle, radioLabelStyle } from './styles'

interface LengthFieldsetProps {
  lengths: EpisodeLengthOption[]
  value: EpisodeLengthId
  onChange: (length: EpisodeLengthId) => void
}

/** The length radios: about 10, 20 or 40 host lines (FR-019). */
export default function LengthFieldset({ lengths, value, onChange }: LengthFieldsetProps) {
  return (
    <fieldset style={fieldsetStyle}>
      <legend style={legendStyle}>Length</legend>
      {lengths.map((length) => (
        <label key={length.length_id} style={radioLabelStyle}>
          <input type="radio" name="podcast-length" value={length.length_id} checked={value === length.length_id} onChange={() => onChange(length.length_id)} />
          <span>
            {length.label} <span style={mutedTextStyle}>(about {length.target_host_lines} host lines)</span>
          </span>
        </label>
      ))}
    </fieldset>
  )
}
