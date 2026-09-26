import { render, screen, fireEvent, within } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import LlmProviderFields, { type LlmSelectionValue } from './LlmProviderFields'
import type { LlmProviderOption } from '../../services/api'

const OLLAMA: LlmProviderOption = {
  provider_id: 'ollama',
  display_name: 'Ollama (local)',
  is_local: true,
  models: [
    { model_id: 'llama3.1:8b', label: 'llama3.1:8b' },
    { model_id: 'llama3.2', label: 'llama3.2' },
  ],
  default_model: 'llama3.1:8b',
  effort_levels: [],
  default_effort: null,
  is_available: true,
  unavailable_reason: null,
  unavailable_message: null,
}

const CLAUDE: LlmProviderOption = {
  provider_id: 'claude',
  display_name: 'Claude (via Claude Code)',
  is_local: false,
  models: [
    { model_id: 'sonnet', label: 'Claude Sonnet' },
    { model_id: 'haiku', label: 'Claude Haiku (fastest)' },
  ],
  default_model: 'sonnet',
  effort_levels: [
    { effort_id: 'low', label: 'Low — fastest replies' },
    { effort_id: 'high', label: 'High — deeper, slower replies' },
  ],
  default_effort: 'low',
  is_available: true,
  unavailable_reason: null,
  unavailable_message: null,
}

const ON_OLLAMA: LlmSelectionValue = { provider: 'ollama', model: 'llama3.1:8b', effort: 'medium' }
const ON_CLAUDE: LlmSelectionValue = { provider: 'claude', model: 'sonnet', effort: 'low' }

function renderFields(value: LlmSelectionValue, providers = [OLLAMA, CLAUDE]) {
  const onChange = vi.fn()
  render(<LlmProviderFields providers={providers} value={value} onChange={onChange} />)
  return onChange
}

const optionTexts = (select: HTMLElement) =>
  within(select)
    .getAllByRole('option')
    .map((option) => option.textContent)

describe('LlmProviderFields', () => {
  it('renders a labelled radio group with one radio per provider', () => {
    renderFields(ON_OLLAMA)

    const group = screen.getByRole('group', { name: /language model/i })
    expect(within(group).getByRole('radio', { name: 'Ollama (local)' })).toBeChecked()
    expect(within(group).getByRole('radio', { name: 'Claude (via Claude Code)' })).not.toBeChecked()
  })

  it("lists only the selected provider's models", () => {
    renderFields(ON_CLAUDE)

    expect(optionTexts(screen.getByLabelText('Model'))).toEqual([
      'Claude Sonnet',
      'Claude Haiku (fastest)',
    ])
  })

  it("choosing another provider selects that provider's default model", () => {
    const onChange = renderFields(ON_OLLAMA)

    fireEvent.click(screen.getByRole('radio', { name: 'Claude (via Claude Code)' }))

    expect(onChange).toHaveBeenCalledWith({ provider: 'claude', model: 'sonnet', effort: 'medium' })
  })

  it('choosing a model reports it', () => {
    const onChange = renderFields(ON_OLLAMA)

    fireEvent.change(screen.getByLabelText('Model'), { target: { value: 'llama3.2' } })

    expect(onChange).toHaveBeenCalledWith({ ...ON_OLLAMA, model: 'llama3.2' })
  })

  it('keeps a saved model that is missing from the list', () => {
    renderFields({ ...ON_OLLAMA, model: 'llama3.1' })

    const select = screen.getByLabelText<HTMLSelectElement>('Model')
    expect(select.value).toBe('llama3.1')
    expect(optionTexts(select)).toContain('llama3.1')
  })

  it('shows effort only for a provider with effort levels', () => {
    renderFields(ON_OLLAMA)

    expect(screen.queryByLabelText('Effort')).not.toBeInTheDocument()
  })

  it('offers the catalogue effort labels for Claude', () => {
    const onChange = renderFields(ON_CLAUDE)
    const effort = screen.getByLabelText<HTMLSelectElement>('Effort')

    expect(optionTexts(effort)).toEqual(['Low — fastest replies', 'High — deeper, slower replies'])
    fireEvent.change(effort, { target: { value: 'high' } })
    expect(onChange).toHaveBeenCalledWith({ ...ON_CLAUDE, effort: 'high' })
  })

  it('renders nothing until the providers have loaded', () => {
    const { container } = render(
      <LlmProviderFields providers={[]} value={ON_OLLAMA} onChange={vi.fn()} />
    )

    expect(container).toBeEmptyDOMElement()
  })
})

const unavailableClaude = (message: string): LlmProviderOption => ({
  ...CLAUDE,
  is_available: false,
  unavailable_reason: 'not_signed_in',
  unavailable_message: message,
})

describe('LlmProviderFields — availability and privacy', () => {
  const SIGN_IN = 'Sign in to Claude Code (run `claude` in a terminal) to use Claude.'

  it('disables an unavailable provider and explains why', () => {
    renderFields(ON_OLLAMA, [OLLAMA, unavailableClaude(SIGN_IN)])

    const radio = screen.getByRole('radio', { name: 'Claude (via Claude Code)' })
    expect(radio).toBeDisabled()
    expect(radio).toHaveAccessibleDescription(SIGN_IN)
    expect(screen.getByText(SIGN_IN)).toBeVisible()
  })

  it('shows no note for an available provider', () => {
    renderFields(ON_OLLAMA)

    expect(screen.getByRole('radio', { name: 'Claude (via Claude Code)' })).not.toHaveAttribute(
      'aria-describedby'
    )
  })

  it('shows what leaves the computer while Claude is selected', () => {
    renderFields(ON_CLAUDE)

    const notice = screen.getByRole('note', { name: /privacy/i })
    expect(notice).toHaveTextContent(/sent to Anthropic/)
    expect(notice).toHaveTextContent(/Claude plan/)
    expect(notice).toHaveTextContent(/audio stay on your computer/)
    expect(notice.getAttribute('style') ?? '').not.toMatch(/#[0-9a-f]{3,8}/i)
  })

  it('shows no privacy notice for the local provider', () => {
    renderFields(ON_OLLAMA)

    expect(screen.queryByRole('note', { name: /privacy/i })).not.toBeInTheDocument()
  })

  it('keeps a saved Claude choice checked after its sign-in is lost', () => {
    renderFields(ON_CLAUDE, [OLLAMA, unavailableClaude(SIGN_IN)])

    expect(screen.getByRole('radio', { name: 'Claude (via Claude Code)' })).toBeChecked()
    expect(screen.getByText(SIGN_IN)).toBeVisible()
    expect(screen.getByLabelText('Model')).toBeInTheDocument()
  })
})
