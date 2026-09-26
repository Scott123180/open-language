import type { CorrectionMode } from '../../services/api'
import RadioCard from './RadioCard'
import {
  fieldsetStyle,
  hintStyle,
  legendStyle,
  warningBodyStyle,
  warningNoteStyle,
  warningTitleStyle,
} from './settingsStyles'

interface CorrectionModeFieldsetProps {
  value: CorrectionMode
  onChange: (mode: CorrectionMode) => void
}

const CORRECTION_MODE_OPTIONS: { value: CorrectionMode; label: string; description: string }[] = [
  {
    value: 'off',
    label: 'Off',
    description: 'No corrections — the conversation runs as it always has.',
  },
  {
    value: 'gentle',
    label: 'Gentle',
    description: 'The character restates your sentence correctly inside its own reply.',
  },
  {
    value: 'strict',
    label: 'Strict',
    description: 'The conversation pauses so you can see the correction and try again.',
  },
]
const CORRECTION_MODE_HINT_ID = 'correction-mode-hint'
const CORRECTION_MODE_WARNING_ID = 'correction-mode-warning'
const CORRECTION_MODE_DESCRIBED_BY = `${CORRECTION_MODE_HINT_ID} ${CORRECTION_MODE_WARNING_ID}`

export default function CorrectionModeFieldset({ value, onChange }: CorrectionModeFieldsetProps) {
  return (
    <fieldset aria-describedby={CORRECTION_MODE_DESCRIBED_BY} style={fieldsetStyle}>
      <legend style={legendStyle}>Correction Feedback</legend>
      {CORRECTION_MODE_OPTIONS.map((option) => (
        <RadioCard
          key={option.value}
          group="correction-mode"
          option={option}
          isChecked={value === option.value}
          onChoose={() => onChange(option.value)}
        />
      ))}
      <CorrectionModeHint />
      <CorrectionAccuracyWarning />
    </fieldset>
  )
}

function CorrectionModeHint() {
  return (
    <p id={CORRECTION_MODE_HINT_ID} style={hintStyle}>
      Gentle and Strict run an extra language-model pass over each message before the character
      answers. Without a GPU this can add several seconds per turn. A check that takes too long is
      skipped so the conversation continues.
    </p>
  )
}

function CorrectionAccuracyWarning() {
  return (
    <aside
      id={CORRECTION_MODE_WARNING_ID}
      role="note"
      aria-label="Correction accuracy"
      style={warningNoteStyle}
    >
      <span style={warningTitleStyle}>Corrections are experimental</span>
      <span style={warningBodyStyle}>
        Corrections come from the language model you selected above, and they can be wrong — a small
        model often flags sentences that were already correct. Treat a correction as a reason to
        double-check, not as the last word. Accuracy improves with a larger model, at the cost of a
        slower reply.
      </span>
    </aside>
  )
}
