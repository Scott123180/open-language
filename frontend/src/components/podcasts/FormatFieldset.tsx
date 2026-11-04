import type { PodcastFormatId, PodcastFormatOption } from '../../services/podcastsApi'
import type { ReactNode } from 'react'
import ChoiceTile from './ChoiceTile'
import { choiceGroupStyle, choiceLegendStyle } from './styles'

interface FormatFieldsetProps {
  formats: PodcastFormatOption[]
  value: PodcastFormatId
  /** A series scope mark after the legend (011 FR-016). */
  mark?: ReactNode
  onChange: (format: PodcastFormatId) => void
}

/** The format tiles: One host, Panel or Listen (FR-003, FR-005). */
export default function FormatFieldset({ formats, value, onChange, mark }: FormatFieldsetProps) {
  return (
    <fieldset style={choiceGroupStyle}>
      <legend style={choiceLegendStyle}>Format{mark}</legend>
      {formats.map((format) => (
        <ChoiceTile key={format.format_id} group="podcast-format" isChecked={value === format.format_id}
          option={{ value: format.format_id, label: format.label, detail: format.description }}
          onChoose={() => onChange(format.format_id)} />
      ))}
    </fieldset>
  )
}
