import type { ConversationLevelId } from '../../services/api'
import { useConversationLevels } from '../../hooks/useConversationLevels'
import ConversationLevelFieldset from './ConversationLevelFieldset'
import { errorTextStyle } from './settingsStyles'

interface ConversationLevelSectionProps {
  value: ConversationLevelId
  onChange: (level: ConversationLevelId) => void
}

/** The level group fed by the shared catalogue, or a plain explanation when it fails to load. */
export default function ConversationLevelSection({
  value,
  onChange,
}: ConversationLevelSectionProps) {
  const { levels, error } = useConversationLevels()
  if (error) {
    return (
      <p role="alert" style={errorTextStyle}>
        {error}
      </p>
    )
  }
  if (levels.length === 0) return null
  return <ConversationLevelFieldset levels={levels} value={value} onChange={onChange} />
}
