import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as podcasts from '../../services/podcastsApi'
import type { PodcastPreferences, PreferencesUpdate } from '../../services/podcastsApi'

export const PODCAST_PREFERENCES_KEY = ['podcast-preferences']

export interface PodcastPreferencesState {
  preferences: PodcastPreferences | undefined
  update: (updates: PreferencesUpdate) => Promise<void>
  saveError: string | null
}

/** The learner's podcast preferences: last format, Show text, interests and name. */
export function usePodcastPreferences(): PodcastPreferencesState {
  const client = useQueryClient()
  const query = useQuery({ queryKey: PODCAST_PREFERENCES_KEY, queryFn: podcasts.getPodcastPreferences })
  const mutation = useMutation({
    mutationFn: (updates: PreferencesUpdate) => podcasts.updatePodcastPreferences(updates),
    onSuccess: (saved) => client.setQueryData(PODCAST_PREFERENCES_KEY, saved),
  })
  const update = async (updates: PreferencesUpdate) => {
    await mutation.mutateAsync(updates).catch(() => undefined)
  }
  return { preferences: query.data, update, saveError: mutation.error ? mutation.error.message : null }
}
