import { useId, useRef, useState } from 'react'
import type { EpisodeOptions, SubjectShow } from '../../services/podcastsApi'
import type { EpisodeSettingsForm } from '../../hooks/podcasts/useEpisodeSettingsForm'
import { useSubjectSuggestions } from '../../hooks/podcasts/useSubjectSuggestions'
import { AskedFieldset, HostLinesFieldset, RoleFieldset, StyleFieldset } from './EpisodeSettingFields'
import SettingsExperimentalNote from './SettingsExperimentalNote'
import SubjectSuggestions from './SubjectSuggestions'
import TodaySubjectField from './TodaySubjectField'
import { secondaryButtonStyle } from './styles'

interface EpisodeSettingsProps {
  options: EpisodeOptions
  form: EpisodeSettingsForm
  /** Listen: nobody is asked anything, so two settings do not apply (FR-011). */
  isListening: boolean
  show: SubjectShow
  seriesId: number | null
  subjectError: string | null
}

/** Episode settings: a closed disclosure named by its summary, so Start stays the one primary
 * action and the defaults need no opening (FR-008, SC-008). */
export default function EpisodeSettings(props: EpisodeSettingsProps) {
  const [isOpen, setIsOpen] = useState(false)
  const panelId = useId()
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
      <button type="button" aria-expanded={isOpen} aria-controls={panelId} onClick={() => setIsOpen(!isOpen)} style={{ ...secondaryButtonStyle, alignSelf: 'flex-start' }}>
        {`Episode settings: ${props.form.summary}`}
      </button>
      {isOpen && <SettingsPanel id={panelId} {...props} />}
    </div>
  )
}

function SettingsPanel({ id, options, form, isListening, show, seriesId, subjectError }: EpisodeSettingsProps & { id: string }) {
  const subjectRef = useRef<HTMLInputElement>(null)
  const suggestions = useSubjectSuggestions(show, seriesId)
  const choose = (subject: string) => {
    form.change('today_subject', subject)
    subjectRef.current?.focus()
  }
  return (
    <div id={id} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
      <SettingsExperimentalNote />
      <StyleFieldset options={options} form={form} />
      <HostLinesFieldset options={options} form={form} />
      {!isListening && <AskedFieldset options={options} form={form} />}
      {!isListening && <RoleFieldset options={options} form={form} />}
      <TodaySubjectField ref={subjectRef} value={form.values.today_subject} maxLength={options.today_subject_max_length} onChange={(v) => form.change('today_subject', v)} error={subjectError} />
      <SubjectSuggestions {...suggestions} onChoose={choose} />
    </div>
  )
}
