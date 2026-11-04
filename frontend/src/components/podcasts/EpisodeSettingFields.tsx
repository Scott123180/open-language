import type { EpisodeOptions } from '../../services/podcastsApi'
import type { EpisodeSettingsForm } from '../../hooks/podcasts/useEpisodeSettingsForm'
import SettingFieldset from './SettingFieldset'

interface FieldsProps {
  options: EpisodeOptions
  form: EpisodeSettingsForm
}

/** Style: how much the hosts talk, explain and tell (FR-006). */
export function StyleFieldset({ options, form }: FieldsProps) {
  const tiles = options.styles.map((s) => ({ value: s.style_id, label: s.label, detail: s.description }))
  return <SettingFieldset legend="Style" options={tiles} value={form.values.style} onChange={(v) => form.change('style', v)} />
}

/** Host lines: how many sentences a host says at a time (FR-002). */
export function HostLinesFieldset({ options, form }: FieldsProps) {
  const tiles = options.line_lengths.map((l) => ({ value: l.line_length_id, label: l.label, detail: '' }))
  return <SettingFieldset legend="Host lines" options={tiles} value={form.values.line_length} onChange={(v) => form.change('line_length', v)} />
}

/** How often you're asked: how often the hosts may hand the learner the turn (FR-003). */
export function AskedFieldset({ options, form }: FieldsProps) {
  const tiles = options.invite_frequencies.map((f) => ({ value: f.invite_frequency_id, label: f.label, detail: '' }))
  return <SettingFieldset legend="How often you're asked" options={tiles} value={form.values.invite_frequency} onChange={(v) => form.change('invite_frequency', v)} />
}

/** Your role: guest, co-host or caller, for this episode only (FR-009). */
export function RoleFieldset({ options, form }: FieldsProps) {
  const tiles = options.learner_roles.map((r) => ({ value: r.learner_role, label: r.label, detail: '' }))
  return <SettingFieldset legend="Your role" options={tiles} value={form.values.learner_role} onChange={(v) => form.change('learner_role', v)} />
}
