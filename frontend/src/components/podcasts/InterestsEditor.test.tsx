import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import InterestsEditor from './InterestsEditor'

const renderEditor = (interests: string[] = [], error: string | null = null) => {
  const onSave = vi.fn().mockResolvedValue(undefined)
  render(<InterestsEditor interests={interests} onSave={onSave} error={error} />)
  return onSave
}

const open = () => fireEvent.click(screen.getByText('Your interests'))

describe('InterestsEditor', () => {
  it('sits behind a "Your interests" disclosure', () => {
    renderEditor()

    expect(screen.getByText('Your interests').tagName).toBe('SUMMARY')
  })

  it('starts on the saved interests', () => {
    renderEditor(['football', 'cooking'])
    open()

    expect(screen.getByLabelText(/Interests/)).toHaveValue('football, cooking')
  })

  it('saves the typed interests as a list', async () => {
    const onSave = renderEditor(['football'])
    open()

    fireEvent.change(screen.getByLabelText(/Interests/), { target: { value: 'football,  cooking , ' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save interests' }))

    await waitFor(() => expect(onSave).toHaveBeenCalledWith(['football', 'cooking']))
  })

  it('clears the interests', async () => {
    const onSave = renderEditor(['football'])
    open()

    fireEvent.click(screen.getByRole('button', { name: 'Clear' }))

    await waitFor(() => expect(onSave).toHaveBeenCalledWith([]))
    expect(screen.getByLabelText(/Interests/)).toHaveValue('')
  })

  it('shows why the interests were refused', () => {
    renderEditor([], 'You can save at most 10 interests.')
    open()

    expect(screen.getByRole('alert')).toHaveTextContent('You can save at most 10 interests.')
  })
})
