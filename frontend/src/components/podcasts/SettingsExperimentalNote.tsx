import { warningBodyStyle, warningNoteStyle, warningTitleStyle } from '../settings/settingsStyles'

// On llama3.1:8b, Medium and Long lines started speaking after more than five seconds, and some
// questions to the learner did not hand them the turn (specs/011-configurable-podcast-shows/
// talk-review-sheet.md, T063, T131). Long Beginner sentences were accepted as they are.
export default function SettingsExperimentalNote() {
  return (
    <aside role="note" aria-label="Episode settings are experimental" style={warningNoteStyle}>
      <span style={warningTitleStyle}>Episode settings are experimental</span>
      <span style={warningBodyStyle}>
        On the local model Medium and Long lines can take a few seconds to start, and a host
        sometimes asks you something without pausing for your answer: press Jump in to reply.
        Short lines start fastest.
      </span>
    </aside>
  )
}
