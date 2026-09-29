import type { PodcastFormatId, PodcastFormatOption } from '../../services/podcastsApi'
import { fieldsetStyle, legendStyle, mutedTextStyle, radioLabelStyle } from './styles'

interface FormatFieldsetProps {
  formats: PodcastFormatOption[]
  value: PodcastFormatId
  onChange: (format: PodcastFormatId) => void
}

/** The format radios: One host, Panel or Listen (FR-003, FR-005). */
export default function FormatFieldset({ formats, value, onChange }: FormatFieldsetProps) {
  return (
    <fieldset style={fieldsetStyle}>
      <legend style={legendStyle}>Format</legend>
      {formats.map((format) => (
        <label key={format.format_id} style={radioLabelStyle}>
          <input type="radio" name="podcast-format" value={format.format_id} checked={value === format.format_id} onChange={() => onChange(format.format_id)} />
          <span>
            {format.label} <span style={mutedTextStyle}>— {format.description}</span>
          </span>
        </label>
      ))}
    </fieldset>
  )
}
