import type { ReactNode } from 'react'
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

/** A labelled native select, the shape every drop-down on the Settings screen shares. */
export default function SelectField(props: SelectFieldProps) {
  return (
    <div style={fieldStyle}>
      <label htmlFor={props.id} style={labelStyle}>
        {props.label}
      </label>
      <select
        id={props.id}
        value={props.value}
        onChange={(e) => props.onChange(e.target.value)}
        aria-describedby={props.describedBy}
        style={controlStyle}
      >
        {props.options.map(selectOption)}
      </select>
      {props.children}
    </div>
  )
}

const selectOption = (option: SelectOption) => (
  <option key={option.value} value={option.value}>
    {option.label}
  </option>
)
