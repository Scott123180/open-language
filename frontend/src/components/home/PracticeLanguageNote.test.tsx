import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import * as api from '../../services/api'
import PracticeLanguageNote from './PracticeLanguageNote'

vi.mock('../../services/api')

const languages = [
  { language_id: 'es', display_name: 'Spanish' },
  { language_id: 'de', display_name: 'German' },
] as api.PracticeLanguageOption[]

const renderNote = () =>
  render(
    <MemoryRouter>
      <PracticeLanguageNote />
    </MemoryRouter>,
  )

describe('PracticeLanguageNote', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.getPracticeLanguages).mockResolvedValue(languages)
    vi.mocked(api.getSettings).mockResolvedValue({ target_language: 'de' } as api.AppSettings)
  })

  it('names the practice language in bold', async () => {
    renderNote()

    const name = await screen.findByText('German')
    expect(name.tagName).toBe('STRONG')
    expect(name.parentElement).toHaveTextContent(/^Practising German/)
  })

  it('links to Settings to change it', async () => {
    renderNote()

    const link = await screen.findByRole('link', { name: 'Change in Settings' })
    expect(link).toHaveAttribute('href', '/settings')
  })

  it('renders nothing while loading', () => {
    vi.mocked(api.getPracticeLanguages).mockReturnValue(new Promise(() => {}))

    const { container } = renderNote()

    expect(container).toBeEmptyDOMElement()
  })

  it('renders nothing when the languages cannot be loaded', async () => {
    vi.mocked(api.getPracticeLanguages).mockRejectedValue(new Error('offline'))

    const { container } = renderNote()

    await waitFor(() => expect(api.getPracticeLanguages).toHaveBeenCalled())
    await new Promise((resolve) => setTimeout(resolve, 0))
    expect(container).toBeEmptyDOMElement()
  })
})
