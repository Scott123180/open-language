import type { PracticeLanguageOption } from '../../services/api'
import RadioCard from './RadioCard'
import { fieldsetStyle, hintStyle, legendStyle } from './settingsStyles'

interface PracticeLanguageFieldsetProps {
  languages: PracticeLanguageOption[]
  value: string
  onChange: (languageId: string) => void
}

const PRACTICE_LANGUAGE_HINT_ID = 'practice-language-hint'

/** The learner-wide practice language (FR-002). A conversation keeps the one it started in. */
export default function PracticeLanguageFieldset({
  languages,
  value,
  onChange,
}: PracticeLanguageFieldsetProps) {
  return (
    <fieldset aria-describedby={PRACTICE_LANGUAGE_HINT_ID} style={fieldsetStyle}>
      <legend style={legendStyle}>Practice language</legend>
      {languages.map((language) => (
        <RadioCard
          key={language.language_id}
          group="practice-language"
          option={{ value: language.language_id, label: language.display_name, description: '' }}
          isChecked={value === language.language_id}
          onChoose={() => onChange(language.language_id)}
        />
      ))}
      <p id={PRACTICE_LANGUAGE_HINT_ID} style={hintStyle}>
        New conversations use this language; existing conversations keep theirs.
      </p>
    </fieldset>
  )
}
