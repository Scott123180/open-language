import type { ReactNode } from 'react'
import ThemedSelect from '../shared/ThemedSelect'
import { controlStyle, fieldStyle, labelStyle } from './settingsStyles'

export interface SelectOption {
  value: string
  label: string
}

interface SelectFieldProps {
  id: string
  label: string
  value: string
  options: SelectOption[]
  onChange: (value: string) => void
  // The id of a hint that describes the current value, announced with the select.
  describedBy?: string
  // Hint text or details shown under the select.
  children?: ReactNode
}

/** A labelled themed drop-down, the shape every drop-down on the Settings screen shares. */
export default function SelectField(props: SelectFieldProps) {
  return (
    <div style={fieldStyle}>
      <label htmlFor={props.id} style={labelStyle}>
        {props.label}
      </label>
      <ThemedSelect
        id={props.id}
        label={props.label}
        value={props.value}
        options={props.options}
        onChange={props.onChange}
        describedBy={props.describedBy}
        style={controlStyle}
      />
      {props.children}
    </div>
  )
}
