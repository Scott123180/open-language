import type { VoiceOption } from '../../services/api'
import SelectField from './SelectField'
import { hintStyle } from './settingsStyles'

interface TtsVoiceFieldProps {
  value: string
  voices: VoiceOption[]
  onChange: (voice: string) => void
}

const QUALITY_LABELS: Record<string, string> = {
  high: 'High quality',
  medium: 'Medium quality',
  low: 'Low quality',
  x_low: 'Low quality (fast)',
}
const NOT_INSTALLED_HINT_ID = 'tts-voice-not-installed'
const NOT_INSTALLED_HINT = 'Not installed. Run ./run.sh --setup to download it.'
const PACE_DESCRIPTIONS: Record<string, { label: string; description: string }> = {
  slow: { label: 'Slow', description: 'Deliberate pace — ideal for beginners' },
  natural: { label: 'Natural', description: 'Conversational native speed' },
  fast: { label: 'Fast', description: 'Quick native pace — ideal for advanced learners' },
}

export default function TtsVoiceField({ value, voices, onChange }: TtsVoiceFieldProps) {
  const selected = voices.find((voice) => voice.key === value)
  return (
    <SelectField
      id="tts-voice"
      label="Voice"
      value={value}
      options={voices.map((voice) => ({ value: voice.key, label: voice.display_name }))}
      onChange={onChange}
      describedBy={selected && !selected.is_installed ? NOT_INSTALLED_HINT_ID : undefined}
    >
      {selected && <VoiceDetails voice={selected} />}
    </SelectField>
  )
}

function VoiceDetails({ voice }: { voice: VoiceOption }) {
  const pace = PACE_DESCRIPTIONS[voice.speaking_rate]
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
      <p style={hintStyle}>{describeVoice(voice)}</p>
      {!voice.is_installed && (
        <p id={NOT_INSTALLED_HINT_ID} role="status" style={hintStyle}>
          {NOT_INSTALLED_HINT}
        </p>
      )}
      {pace && (
        <p style={hintStyle}>
          Pace: <strong style={{ color: 'var(--color-text)' }}>{pace.label}</strong> —{' '}
          {pace.description}
        </p>
      )}
    </div>
  )
}

function describeVoice(voice: VoiceOption): string {
  const regionCode = voice.locale.split('_')[1]
  const country = new Intl.DisplayNames(['en'], { type: 'region' }).of(regionCode) ?? regionCode
  const genderIcon = voice.gender === 'female' ? '♀' : '♂'
  const gender = voice.gender.charAt(0).toUpperCase() + voice.gender.slice(1)
  const quality = QUALITY_LABELS[voice.quality] ?? voice.quality
  return `${genderIcon} ${gender} · ${country} · ${quality}`
}
