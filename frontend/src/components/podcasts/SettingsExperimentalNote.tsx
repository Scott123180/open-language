import { warningBodyStyle, warningNoteStyle, warningTitleStyle } from '../settings/settingsStyles'

// On llama3.1:8b, Beginner sentences ran long and Medium and Long lines started speaking after
// more than five seconds (specs/011-configurable-podcast-shows/talk-review-sheet.md, T063, T131).
export default function SettingsExperimentalNote() {
  return (
    <aside role="note" aria-label="Episode settings are experimental" style={warningNoteStyle}>
      <span style={warningTitleStyle}>Episode settings are experimental</span>
      <span style={warningBodyStyle}>
        On the local model the hosts often speak in longer, harder sentences than your level, and
        Medium and Long lines can take a few seconds to start. Short lines start fastest.
      </span>
    </aside>
  )
}
