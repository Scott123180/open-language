import { fireEvent, screen, within } from '@testing-library/react'

type Name = string | RegExp

/** Open the themed drop-down named `label` and choose the option named `option`. */
export function chooseOption(label: Name, option: Name): void {
  fireEvent.click(screen.getByRole('combobox', { name: label }))
  fireEvent.click(within(screen.getByRole('listbox')).getByRole('option', { name: option }))
}

/** The option labels of the themed drop-down named `label`, read by opening it. */
export function optionLabels(label: Name): string[] {
  const combobox = screen.getByRole('combobox', { name: label })
  fireEvent.click(combobox)
  const labels = within(screen.getByRole('listbox')).getAllByRole('option').map((option) => option.textContent ?? '')
  fireEvent.keyDown(combobox, { key: 'Escape' })
  return labels
}
