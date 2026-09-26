import type { CSSProperties } from 'react'
import type { ConversationLevelId, ConversationLevelOption } from '../../services/api'
import { useConversationLevelSetting } from './useConversationLevelSetting'
import type { ConversationLevelSetting } from './useConversationLevelSetting'

const SELECT_ID = 'conversation-level-select'
const DESCRIPTION_ID = 'conversation-level-description'

const wrapperStyle: CSSProperties = { position: 'relative', display: 'flex', alignItems: 'center' }
const selectStyle: CSSProperties = {
  minHeight: '44px',
  minWidth: '44px',
  padding: '0 8px',
  background: 'transparent',
  color: 'var(--color-text-muted)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius)',
  font: 'inherit',
  fontSize: '0.85rem',
  cursor: 'pointer',
}
const visuallyHidden: CSSProperties = {
  position: 'absolute',
  width: '1px',
  height: '1px',
  padding: 0,
  margin: '-1px',
  overflow: 'hidden',
  clip: 'rect(0, 0, 0, 0)',
  whiteSpace: 'nowrap',
  border: 0,
}
const errorStyle: CSSProperties = {
  position: 'absolute',
  top: 'calc(100% + 6px)',
  right: 0,
  zIndex: 10,
  width: 'max-content',
  maxWidth: '260px',
  margin: 0,
  padding: '8px 12px',
  background: 'var(--color-surface-raised)',
  color: 'var(--color-error)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-lg)',
  boxShadow: 'var(--shadow-md)',
  fontSize: '0.85rem',
}

/** The chat header's level switcher: secondary to Send, saves on change (contract §5). */
export default function ConversationLevelControl() {
  const setting = useConversationLevelSetting()
  const selected = setting.levels.find((option) => option.level_id === setting.level)
  if (!selected && !setting.error) return null
  return (
    <div style={wrapperStyle}>
      {selected && <LevelSelect setting={setting} selected={selected} />}
      {selected && (
        <span id={DESCRIPTION_ID} style={visuallyHidden}>
          {selected.description}
        </span>
      )}
      <LevelFeedback announcement={setting.announcement} error={setting.error} />
    </div>
  )
}

interface LevelSelectProps {
  setting: ConversationLevelSetting
  selected: ConversationLevelOption
}

function LevelSelect({ setting, selected }: LevelSelectProps) {
  return (
    <>
      <label htmlFor={SELECT_ID} style={visuallyHidden}>
        Level
      </label>
      <select
        id={SELECT_ID}
        value={selected.level_id}
        disabled={setting.isSaving}
        aria-describedby={DESCRIPTION_ID}
        onChange={(e) => setting.changeLevel(e.target.value as ConversationLevelId)}
        style={selectStyle}
      >
        {setting.levels.map(levelOption)}
      </select>
    </>
  )
}

const levelOption = (option: ConversationLevelOption) => (
  <option key={option.level_id} value={option.level_id}>
    {optionText(option)}
  </option>
)

function LevelFeedback({
  announcement,
  error,
}: {
  announcement: string | null
  error: string | null
}) {
  return (
    <>
      <span aria-live="polite" style={visuallyHidden}>
        {announcement}
      </span>
      {error && (
        <p role="alert" style={errorStyle}>
          {error}
        </p>
      )}
    </>
  )
}

// Natural has no CEFR level ("No limit"), so it reads as its name alone.
const optionText = (option: ConversationLevelOption) =>
  option.level_id === 'natural' ? option.label : `${option.label} (${option.cefr_label})`
