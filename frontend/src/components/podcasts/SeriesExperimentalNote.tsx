import { warningBodyStyle, warningNoteStyle, warningTitleStyle } from '../settings/settingsStyles'

// The default local model invented memories and repeated topics in the 010 recall benchmark
// (specs/010-recurring-podcast-shows/series-review-sheet.md, tasks T064, T135).
export default function SeriesExperimentalNote() {
  return (
    <aside role="note" aria-label="Series are experimental" style={warningNoteStyle}>
      <span style={warningTitleStyle}>Series are experimental</span>
      <span style={warningBodyStyle}>
        The hosts usually remember what you told them, but on the local model they sometimes
        recall things you never said, or come back to an earlier topic. You can see what they
        remember on this screen, and start the series over at any time.
      </span>
    </aside>
  )
}
