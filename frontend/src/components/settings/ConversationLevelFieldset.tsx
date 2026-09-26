import type { ConversationLevelId, ConversationLevelOption } from '../../services/api'
import RadioCard from './RadioCard'
import {
  fieldsetStyle,
  legendStyle,
  warningBodyStyle,
  warningNoteStyle,
  warningTitleStyle,
} from './settingsStyles'

interface ConversationLevelFieldsetProps {
  levels: ConversationLevelOption[]
  value: ConversationLevelId
  onChange: (level: ConversationLevelId) => void
}

const LEVEL_WARNING_ID = 'conversation-level-warning'

/** The level radios on Settings; saved by the page's Save along with everything else. */
export default function ConversationLevelFieldset(props: ConversationLevelFieldsetProps) {
  const { levels, value, onChange } = props
  return (
    <fieldset aria-describedby={LEVEL_WARNING_ID} style={fieldsetStyle}>
      <legend style={legendStyle}>Conversation level</legend>
      {levels.map((level) => (
        <RadioCard
          key={level.level_id}
          group="conversation-level"
          option={toRadioOption(level)}
          isChecked={value === level.level_id}
          onChoose={() => onChange(level.level_id)}
        />
      ))}
      <LevelAccuracyWarning />
    </fieldset>
  )
}

const toRadioOption = (level: ConversationLevelOption) => ({
  value: level.level_id,
  label: level.label,
  description: level.description,
  badge: level.cefr_label,
})

// The default local model missed the Beginner target in the 005 benchmark (tasks T041, T042).
function LevelAccuracyWarning() {
  return (
    <aside id={LEVEL_WARNING_ID} role="note" aria-label="Level accuracy" style={warningNoteStyle}>
      <span style={warningTitleStyle}>Levels are experimental</span>
      <span style={warningBodyStyle}>
        The local model does not always keep to the level — especially at Beginner, some replies run
        longer than the level allows. If you get lost, ask the character to speak more simply. A
        larger model that follows the level more closely is on the roadmap.
      </span>
    </aside>
  )
}
