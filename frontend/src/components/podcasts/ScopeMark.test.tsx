import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import ScopeMark from './ScopeMark'

describe('ScopeMark (011 FR-016)', () => {
  it.each([
    ['this-episode', 'this episode'],
    ['from-now-on', 'from now on'],
  ] as const)('reads %s as “%s”', (scope, text) => {
    render(<legend>Style<ScopeMark scope={scope} /></legend>)

    expect(screen.getByText(text, { exact: false })).toBeInTheDocument()
  })

  it('shows nothing for a usual setting', () => {
    const { container } = render(<ScopeMark scope={undefined} />)

    expect(container).toBeEmptyDOMElement()
  })
})
