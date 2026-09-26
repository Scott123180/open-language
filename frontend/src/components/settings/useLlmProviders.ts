import { useEffect, useState } from 'react'
import * as api from '../../services/api'

/** The provider catalogue with live availability; empty until it loads. */
export function useLlmProviders(): api.LlmProviderOption[] {
  const [providers, setProviders] = useState<api.LlmProviderOption[]>([])

  useEffect(() => {
    // A failed load leaves the provider fields hidden; the saved choice still round-trips.
    api
      .getLlmProviders()
      .then(setProviders)
      .catch(() => {})
  }, [])

  return providers
}
