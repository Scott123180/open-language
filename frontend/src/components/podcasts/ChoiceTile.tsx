import { choiceDetailStyle, choiceLabelStyle, choiceTileStyle } from './styles'

export interface ChoiceTileOption {
  value: string
  label: string
  detail: string
}

interface ChoiceTileProps {
  /** The radio group's name. */
  group: string
  option: ChoiceTileOption
  isChecked: boolean
  onChoose: () => void
}

/** One radio in a selection tile: the label over its detail, highlighted when chosen. */
export default function ChoiceTile({ group, option, isChecked, onChoose }: ChoiceTileProps) {
  return (
    <label style={choiceTileStyle(isChecked)}>
      <input type="radio" name={group} value={option.value} checked={isChecked} onChange={onChoose}
        style={{ marginTop: '4px', accentColor: 'var(--color-primary)' }} />
      <span style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
        <span style={choiceLabelStyle(isChecked)}>{option.label}</span>
        <span style={choiceDetailStyle(isChecked)}>{option.detail}</span>
      </span>
    </label>
  )
}
