import { radioLabelStyle } from './styles'

interface ShowTextSwitchProps {
  isOn: boolean
  onChange: (isOn: boolean) => void
}

/** Listen's Show text: every line in full, remembered across episodes (FR-043). */
export default function ShowTextSwitch({ isOn, onChange }: ShowTextSwitchProps) {
  return (
    <label style={{ ...radioLabelStyle, alignItems: 'center', padding: '0 var(--space-4)' }}>
      <input type="checkbox" role="switch" aria-checked={isOn} checked={isOn} onChange={(e) => onChange(e.target.checked)} />
      Show text
    </label>
  )
}
