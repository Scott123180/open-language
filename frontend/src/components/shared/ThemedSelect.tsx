import { useEffect, useId, useRef, type CSSProperties } from 'react'
import { IconCheck } from './icons'
import { useListboxNavigation, type ListboxNavigation } from './useListboxNavigation'

export interface ThemedSelectOption {
  value: string
  label: string
}

interface ThemedSelectProps {
  label: string
  value: string
  options: ThemedSelectOption[]
  onChange: (value: string) => void
  id?: string
  describedBy?: string
  disabled?: boolean
  style?: CSSProperties
  /** Sized to its content, with the open list aligned to its right edge (a header control). */
  isCompact?: boolean
}

/**
 * A drop-down drawn in the app's theme: the WAI-ARIA select-only combobox (010 research R11).
 * A native select's open list is drawn by the browser and the OS, so it ignores the theme.
 * Focus stays on the trigger; the active option is announced through aria-activedescendant.
 */
export default function ThemedSelect(props: ThemedSelectProps) {
  const listId = `${useId()}-listbox`
  const selectedIndex = props.options.findIndex((option) => option.value === props.value)
  const nav = useListboxNavigation(
    props.options.map((option) => option.label),
    selectedIndex,
    (index) => props.onChange(props.options[index].value),
  )
  return (
    <div style={props.isCompact ? compactWrapperStyle : wrapperStyle}>
      <SelectTrigger {...props} nav={nav} listId={listId} selectedIndex={selectedIndex} />
      {nav.isOpen && <OptionList options={props.options} nav={nav} listId={listId} label={props.label} selectedIndex={selectedIndex} isCompact={props.isCompact} />}
    </div>
  )
}

interface PartProps {
  nav: ListboxNavigation
  listId: string
  selectedIndex: number
}

const comboboxAria = ({ nav, listId, label, describedBy }: ThemedSelectProps & PartProps) => ({
  role: 'combobox',
  'aria-label': label,
  'aria-haspopup': 'listbox' as const,
  'aria-expanded': nav.isOpen,
  'aria-controls': listId,
  'aria-activedescendant': nav.isOpen ? optionId(listId, nav.activeIndex) : undefined,
  'aria-describedby': describedBy,
})

function SelectTrigger(props: ThemedSelectProps & PartProps) {
  const { nav } = props
  return (
    <button
      type="button"
      {...comboboxAria(props)}
      id={props.id}
      disabled={props.disabled}
      onClick={() => (nav.isOpen ? nav.close() : nav.open())}
      onKeyDown={nav.onKeyDown}
      onBlur={nav.close}
      className="themed-select-trigger"
      style={{ ...triggerStyle, ...props.style }}
    >
      {props.options[props.selectedIndex]?.label ?? ''}
    </button>
  )
}

function OptionList(props: PartProps & { options: ThemedSelectOption[]; label: string; isCompact?: boolean }) {
  const listRef = useRef<HTMLUListElement>(null)
  const { nav, listId } = props
  useEffect(() => {
    listRef.current?.querySelector('.themed-select-option--active')?.scrollIntoView?.({ block: 'nearest' })
  }, [nav.activeIndex])
  return (
    <ul ref={listRef} role="listbox" id={listId} aria-label={props.label} tabIndex={-1} className={`themed-select-list${props.isCompact ? ' themed-select-list--compact' : ''}`}>
      {props.options.map((option, index) => (
        <OptionItem key={option.value} option={option} index={index} {...props} />
      ))}
    </ul>
  )
}

function OptionItem(props: PartProps & { option: ThemedSelectOption; index: number }) {
  const { nav, index } = props
  const isSelected = index === props.selectedIndex
  const className = `themed-select-option${index === nav.activeIndex ? ' themed-select-option--active' : ''}`
  return (
    <li
      role="option"
      id={optionId(props.listId, index)}
      aria-selected={isSelected}
      className={className}
      onMouseDown={(event) => event.preventDefault()}
      onClick={() => nav.choose(index)}
    >
      <span style={checkSlotStyle}>{isSelected && <IconCheck size={16} />}</span>
      {props.option.label}
    </li>
  )
}

const optionId = (listId: string, index: number) => `${listId}-option-${index}`

const wrapperStyle: CSSProperties = { position: 'relative', width: '100%' }
const compactWrapperStyle: CSSProperties = { position: 'relative', display: 'inline-block' }
const triggerStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 'var(--space-2)',
  width: '100%',
  padding: '10px 12px',
  borderRadius: 'var(--radius)',
  border: '1px solid var(--color-border)',
  background: 'var(--color-surface)',
  color: 'var(--color-text)',
  fontSize: '1rem',
  textAlign: 'left',
}
const checkSlotStyle: CSSProperties = { display: 'inline-flex', width: '16px', flexShrink: 0 }
