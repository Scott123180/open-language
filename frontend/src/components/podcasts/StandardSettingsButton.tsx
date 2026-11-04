import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import * as podcasts from '../../services/podcastsApi'
import type { SeriesDetail } from '../../services/podcastsApi'
import { seriesKey } from '../../hooks/podcasts/useSeries'
import ConfirmDialog from '../shared/ConfirmDialog'
import ErrorBanner from '../shared/ErrorBanner'
import { secondaryButtonStyle } from './styles'

interface StandardSettingsButtonProps {
  detail: SeriesDetail
  /** The form forgets its changes, so it shows the standard settings at once. */
  onReset: () => void
}

/** Use the show's standard settings: shown only when the series has its own (011 FR-019). */
export default function StandardSettingsButton({ detail, onReset }: StandardSettingsButtonProps) {
  const [isAsking, setIsAsking] = useState(false)
  const reset = useStandardReset(detail.series_id, () => {
    setIsAsking(false)
    onReset()
  })
  if (detail.is_standard !== false) return null
  return (
    <>
      <button type="button" onClick={() => setIsAsking(true)} style={{ ...secondaryButtonStyle, alignSelf: 'flex-start' }}>Use the show's standard settings</button>
      {isAsking && (
        <ConfirmDialog title="Use the show's standard settings?" message="Later episodes go back to One host, Medium, Balanced, Medium lines and Sometimes. Past episodes keep theirs."
          confirmLabel="Use standard settings" isBusy={reset.isPending} onConfirm={() => reset.mutate()} onCancel={() => setIsAsking(false)}>
          {reset.error && <ErrorBanner message={reset.error.message} />}
        </ConfirmDialog>
      )}
    </>
  )
}

/** The reset, with the series' fresh detail put where the setup reads it. */
function useStandardReset(seriesId: number, onDone: () => void) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => podcasts.resetSeriesSettings(seriesId),
    onSuccess: (fresh) => {
      queryClient.setQueryData(seriesKey(seriesId), fresh)
      onDone()
    },
  })
}
