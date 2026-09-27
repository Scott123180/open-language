# Validation record (006)

What was checked, how, and what was not. Benchmark figures are in
[benchmark-results.md](benchmark-results.md).

## Accessibility (T104)

A human screen-reader pass was **not** done in this session. Instead a throwaway Playwright audit
measured the same properties in Chromium, in the light and dark themes:

| Check | Light | Dark |
|---|---|---|
| Practice-language radios: group named "Practice language"; ArrowDown moves Spanish → German | pass | pass |
| Radio card target height | 48 px | 48 px |
| Settings hint contrast (fieldset and "Not installed" hint) | 4.56:1 | 4.56:1 |
| "Not installed" hint is `role="status"` and linked by `aria-describedby` to the Voice select | pass | pass |
| Home note text / name / link contrast | 4.56 / 16.62 / 4.56 | 6.28 / 15.99 / 6.28 |
| Home link: underlined (not colour alone) | pass | pass |
| Past Chats language tag contrast; tag is part of the row's accessible name | 4.80:1 | 5.70:1 |
| Chat voice notice is `role="status"`, contrast | 4.80:1 | 5.70:1 |
| Chat header tag announced as "Conversation language: German", contrast | 4.80:1 | 5.70:1 |

One fix came out of it: the Home "Change in Settings" link was 21 px tall; it now has a 44 px
minimum target.
