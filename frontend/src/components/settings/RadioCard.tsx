import {
  radioBadgeStyle,
  radioCardStyle,
  radioDescriptionStyle,
  radioLabelStyle,
  radioTextStyle,
} from './settingsStyles'

export interface RadioCardOption {
  value: string
  label: string
  description: string
  // Shown after the label and read as part of the radio's name, e.g. a CEFR level.
  badge?: string
}

interface RadioCardProps {
  // The radio group's name, which also prefixes every id in the card.
  group: string
  option: RadioCardOption
  isChecked: boolean
  onChoose: () => void
}

/** A radio in a bordered card, named by its label and described by its description. */
export default function RadioCard({ group, option, isChecked, onChoose }: RadioCardProps) {
  const { id, labelId, descriptionId } = radioCardIds(group, option.value)
  return (
    <label htmlFor={id} style={radioCardStyle(isChecked)}>
      <input
        {...{ id, name: group, value: option.value, checked: isChecked, onChange: onChoose }}
        type="radio"
        aria-labelledby={labelId}
        aria-describedby={descriptionId}
        style={{ marginTop: '3px' }}
      />
      <span style={radioTextStyle}>
        <RadioCardLabel id={labelId} option={option} />
        <span id={descriptionId} style={radioDescriptionStyle}>
          {option.description}
        </span>
      </span>
    </label>
  )
}

function radioCardIds(group: string, value: string) {
  const id = `${group}-${value}`
  return { id, labelId: `${id}-label`, descriptionId: `${id}-description` }
}

function RadioCardLabel({ id, option }: { id: string; option: RadioCardOption }) {
  return (
    <span id={id} style={radioLabelStyle}>
      {option.label}
      {option.badge && <span style={radioBadgeStyle}> {option.badge}</span>}
    </span>
  )
}
