import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import SelfAssessmentBar from './SelfAssessmentBar'

describe('SelfAssessmentBar', () => {
  it('renders three rating buttons', () => {
    render(<SelfAssessmentBar onRate={vi.fn()} />)
    expect(screen.getByRole('button', { name: /didn't know/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /guessed correctly/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /knew it/i })).toBeInTheDocument()
  })

  it('calls onRate with "didnt_know" when Didn\'t Know is clicked', () => {
    const onRate = vi.fn()
    render(<SelfAssessmentBar onRate={onRate} />)
    fireEvent.click(screen.getByRole('button', { name: /didn't know/i }))
    expect(onRate).toHaveBeenCalledWith('didnt_know')
  })

  it('calls onRate with "guessed" when Guessed Correctly is clicked', () => {
    const onRate = vi.fn()
    render(<SelfAssessmentBar onRate={onRate} />)
    fireEvent.click(screen.getByRole('button', { name: /guessed correctly/i }))
    expect(onRate).toHaveBeenCalledWith('guessed')
  })

  it('calls onRate with "knew_it" when Knew It is clicked', () => {
    const onRate = vi.fn()
    render(<SelfAssessmentBar onRate={onRate} />)
    fireEvent.click(screen.getByRole('button', { name: /knew it/i }))
    expect(onRate).toHaveBeenCalledWith('knew_it')
  })
})
