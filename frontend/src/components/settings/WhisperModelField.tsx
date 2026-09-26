import SelectField from './SelectField'
import { hintStyle } from './settingsStyles'

interface WhisperModelFieldProps {
  value: string
  onChange: (model: string) => void
}

const WHISPER_MODEL_OPTIONS = [
  { value: 'base', label: 'Base — fast, lower accuracy' },
  { value: 'small', label: 'Small — balanced' },
  { value: 'medium', label: 'Medium — slower, higher accuracy' },
]

export default function WhisperModelField({ value, onChange }: WhisperModelFieldProps) {
  return (
    <SelectField
      id="whisper-model"
      label="Speech Recognition Model"
      value={value}
      options={WHISPER_MODEL_OPTIONS}
      onChange={onChange}
    >
      <p style={hintStyle}>
        Takes effect on next recording. Larger models load once then stay in memory.
      </p>
    </SelectField>
  )
}
