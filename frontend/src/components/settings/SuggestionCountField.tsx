import { controlStyle, fieldStyle, labelStyle } from './settingsStyles'

interface SuggestionCountFieldProps {
  value: number
  onChange: (count: number) => void
}

const MIN_SUGGESTIONS = 1
const MAX_SUGGESTIONS = 5

export default function SuggestionCountField({ value, onChange }: SuggestionCountFieldProps) {
  return (
    <div style={fieldStyle}>
      <label htmlFor="suggestion-count" style={labelStyle}>
        Suggestion Count ({MIN_SUGGESTIONS}–{MAX_SUGGESTIONS})
      </label>
      <input
        id="suggestion-count"
        type="number"
        min={MIN_SUGGESTIONS}
        max={MAX_SUGGESTIONS}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{ ...controlStyle, width: '80px' }}
      />
    </div>
  )
}
