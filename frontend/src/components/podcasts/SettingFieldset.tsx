import { useId } from 'react'
import type { ReactNode } from 'react'
import ChoiceTile from './ChoiceTile'
import type { ChoiceTileOption } from './ChoiceTile'
import { choiceGroupStyle, choiceLegendStyle } from './styles'

interface SettingFieldsetProps<T extends string> {
  legend: string
  options: (ChoiceTileOption & { value: T })[]
  value: T
  onChange: (value: T) => void
  /** Text after the legend, such as a series scope mark (011 FR-016). */
  mark?: ReactNode
}

/** One Episode setting as a radio group with a legend, built like the format tiles (R16). */
export default function SettingFieldset<T extends string>({ legend, options, value, onChange, mark }: SettingFieldsetProps<T>) {
  const legendId = useId()
  return (
    <fieldset role="radiogroup" aria-labelledby={legendId} style={choiceGroupStyle}>
      <legend id={legendId} style={choiceLegendStyle}>{legend}{mark}</legend>
      {options.map((option) => (
        <ChoiceTile key={option.value} group={legendId} isChecked={value === option.value} option={option} onChoose={() => onChange(option.value)} />
      ))}
    </fieldset>
  )
}
