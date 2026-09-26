import type { CSSProperties } from 'react'
import type { LlmProviderOption } from '../../services/api'

export interface LlmSelectionValue {
  provider: string
  model: string
  effort: string
}

interface LlmProviderFieldsProps {
  providers: LlmProviderOption[]
  value: LlmSelectionValue
  onChange: (value: LlmSelectionValue) => void
}

const MODEL_SELECT_ID = 'llm-model'
const PRIVACY_NOTICE_ID = 'llm-privacy-notice'
const EFFORT_SELECT_ID = 'llm-effort'

const fieldStyle: CSSProperties = { display: 'flex', flexDirection: 'column', gap: '6px' }
const fieldsetStyle: CSSProperties = { ...fieldStyle, border: 'none', padding: 0, margin: 0 }
const labelStyle: CSSProperties = { fontWeight: 600, color: 'var(--color-text)' }
const selectStyle: CSSProperties = {
  padding: '10px 12px',
  borderRadius: 'var(--radius)',
  border: '1px solid var(--color-border)',
  background: 'var(--color-surface)',
  color: 'var(--color-text)',
  fontSize: '1rem',
}
const noteStyle: CSSProperties = {
  borderLeft: '3px solid var(--color-warning)',
  background: 'var(--color-surface-raised)',
  borderRadius: 'var(--radius-lg)',
  boxShadow: 'var(--shadow-sm)',
  padding: '10px 14px',
  fontSize: '0.85rem',
  color: 'var(--color-text)',
  lineHeight: 'var(--leading-relaxed)',
}
const unavailableNoteStyle: CSSProperties = {
  margin: '0 0 0 12px',
  fontSize: '0.85rem',
  color: 'var(--color-text-muted)',
}
const radioCardStyle = (isChecked: boolean, isAvailable: boolean): CSSProperties => ({
  display: 'flex',
  alignItems: 'center',
  gap: '10px',
  padding: '10px 12px',
  minHeight: '44px',
  borderRadius: 'var(--radius-lg)',
  border: '1px solid var(--color-border)',
  background: isChecked ? 'var(--color-surface-raised)' : 'var(--color-surface)',
  color: isAvailable ? 'var(--color-text)' : 'var(--color-text-muted)',
  cursor: isAvailable ? 'pointer' : 'not-allowed',
})

/** Provider radios, then the chosen provider's models, then effort when it has levels. */
export default function LlmProviderFields({ providers, value, onChange }: LlmProviderFieldsProps) {
  const selected = providers.find((p) => p.provider_id === value.provider)
  if (!selected) return null
  return (
    <fieldset style={fieldsetStyle}>
      <legend style={{ ...labelStyle, padding: 0 }}>Language model</legend>
      <ProviderRadios providers={providers} value={value} onChange={onChange} />
      <ModelSelect provider={selected} value={value} onChange={onChange} />
      {selected.effort_levels.length > 0 && (
        <EffortSelect provider={selected} value={value} onChange={onChange} />
      )}
      {selected.privacy_notice && <PrivacyNotice notice={selected.privacy_notice} />}
    </fieldset>
  )
}

function ProviderRadios({ providers, value, onChange }: LlmProviderFieldsProps) {
  // A new provider brings its own default model (FR-024); effort is kept for later.
  const choose = (provider: LlmProviderOption) =>
    onChange({ ...value, provider: provider.provider_id, model: provider.default_model })
  return (
    <>
      {providers.map((provider) => (
        <ProviderRadio
          key={provider.provider_id}
          provider={provider}
          isChecked={provider.provider_id === value.provider}
          onChoose={() => choose(provider)}
        />
      ))}
    </>
  )
}

interface ProviderRadioProps {
  provider: LlmProviderOption
  isChecked: boolean
  onChoose: () => void
}

function ProviderRadio({ provider, isChecked, onChoose }: ProviderRadioProps) {
  const id = `llm-provider-${provider.provider_id}`
  const noteId = `${id}-unavailable`
  return (
    <div style={fieldStyle}>
      <label htmlFor={id} style={radioCardStyle(isChecked, provider.is_available)}>
        <input
          id={id}
          type="radio"
          name="llm-provider"
          checked={isChecked}
          onChange={onChoose}
          {...availabilityProps(provider, noteId)}
        />
        <span style={{ fontWeight: 600 }}>{provider.display_name}</span>
      </label>
      {!provider.is_available && <UnavailableNote id={noteId} provider={provider} />}
    </div>
  )
}

/** An unavailable provider can't be chosen, and its radio says why (Principle IV). */
const availabilityProps = (provider: LlmProviderOption, noteId: string) =>
  provider.is_available ? {} : { disabled: true, 'aria-describedby': noteId }

function UnavailableNote({ id, provider }: { id: string; provider: LlmProviderOption }) {
  return (
    <p id={id} style={unavailableNoteStyle}>
      {provider.unavailable_message}
    </p>
  )
}

/** The catalogue's own words for what leaves the machine (Principle VI). */
function PrivacyNotice({ notice }: { notice: string }) {
  return (
    <aside id={PRIVACY_NOTICE_ID} role="note" aria-label="Privacy" style={noteStyle}>
      {notice}
    </aside>
  )
}

interface ProviderSelectProps {
  provider: LlmProviderOption
  value: LlmSelectionValue
  onChange: (value: LlmSelectionValue) => void
}

function ModelSelect({ provider, value, onChange }: ProviderSelectProps) {
  // An installed local model the catalogue doesn't list stays selectable (spec Assumptions).
  const isListed = provider.models.some((m) => m.model_id === value.model)
  const unlisted = isListed ? [] : [{ id: value.model, label: value.model }]
  const listed = provider.models.map((m) => ({ id: m.model_id, label: m.label }))
  return (
    <LabelledSelect
      id={MODEL_SELECT_ID}
      label="Model"
      value={value.model}
      choices={[...unlisted, ...listed]}
      onPick={(model) => onChange({ ...value, model })}
    />
  )
}

function EffortSelect({ provider, value, onChange }: ProviderSelectProps) {
  return (
    <LabelledSelect
      id={EFFORT_SELECT_ID}
      label="Effort"
      value={value.effort}
      choices={provider.effort_levels.map((e) => ({ id: e.effort_id, label: e.label }))}
      onPick={(effort) => onChange({ ...value, effort })}
    />
  )
}

interface LabelledSelectProps {
  id: string
  label: string
  value: string
  choices: { id: string; label: string }[]
  onPick: (choiceId: string) => void
}

function LabelledSelect({ id, label, value, choices, onPick }: LabelledSelectProps) {
  return (
    <div style={fieldStyle}>
      <label htmlFor={id} style={labelStyle}>
        {label}
      </label>
      <select id={id} value={value} onChange={(e) => onPick(e.target.value)} style={selectStyle}>
        {choices.map((choice) => (
          <option key={choice.id} value={choice.id}>
            {choice.label}
          </option>
        ))}
      </select>
    </div>
  )
}
