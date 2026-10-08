# UI Contract: Language Switcher in the Header

**Feature**: 009-language-switcher-header

The observable contract the Vitest and Playwright tests assert. Roles and names are what tests query
by; styles follow `docs/design-system.md`.

## Where the header appears

| Route | Shared header with switcher | Language shown |
|---|---|---|
| `/`, `/podcasts`, `/podcasts/setup`, `/history`, `/flashcards`, `/flashcards/decks`, `/flashcards/analytics`, `/settings` | yes (`AppHeader`) | current practice language |
| `/chat/:id` | no (own header) | the conversation's language, read-only, with flag |
| `/podcasts/episodes/:id` | no (own header) | the episode's language, read-only, with flag |
| `/flashcards/practice/:id`, `/flashcards/summary/:id` | no (own layout) | none (unchanged) |

Each screen has exactly one `banner` landmark.

## `AppHeader`

- `role="banner"` containing, in order: a link "Open Language" to `/`; the language control; the
  theme toggle (moved unchanged from Home: name "Switch to dark mode" / "Switch to light mode").
- Height 56px, `--color-surface` background, bottom border `--color-border`, sticky at the top, as
  Home's header is today.

## Language control (closed)

| Aspect | Contract |
|---|---|
| Role / name | `button`, name `Practice language: {display_name}` |
| ARIA | `aria-haspopup="listbox"`, `aria-expanded="false"` |
| Content | flag (decorative) + `display_name` + a chevron (decorative) |
| ≥ 400px wide | flag and name visible |
| < 400px wide | flag visible, name visually hidden (still in the accessible name) |
| Loading | name `Practice language`, no flag, disabled |
| Catalogue failed | name `Practice language`, enabled; opening shows the load error |
| Unknown saved code | name `Practice language: {code}`, no flag |
| Saving | `aria-busy="true"`, shows the previous language until the save succeeds |
| Size / colour | ≥ 44×44px; text `--color-text`; hover/focus as `.nav-pill` |

## Switcher (open)

```text
┌─────────────────────────────┐
│ MY LANGUAGES                │   ← group heading, --color-text-muted, uppercase label style
│ [ES] Spanish            ✓  │   ← option, aria-selected="true"
│ [DE] German                │
│ START A NEW LANGUAGE        │
│ [IT] Italian               │
└─────────────────────────────┘
```

| Aspect | Contract |
|---|---|
| Container | `role="listbox"`, name `Practice language` |
| Groups | `role="group"`, named `My languages` / `Start a new language` by their visible headings; an empty group is not rendered |
| Options | `role="option"`, name = `display_name` only (the flag is `aria-hidden`); current has `aria-selected="true"` |
| Order | My languages: current, then `has_activity` languages in catalogue order. Start a new language: the rest, catalogue order |
| Opening | focus moves to the listbox with the current option active (`aria-activedescendant`) |
| Keys | ↓/↑ next/previous option across groups (no wrap), Home/End first/last, Enter/Space choose, Escape close |
| Pointer | click an option chooses; click outside closes |
| Choose current | closes, no request |
| Choose another | `PUT /api/settings {target_language}`; on success closes, control shows the new language, focus returns to the control |
| Escape / outside | closes, no request, focus returns to the control |
| Save failed | stays open; `role="alert"` inside the popup: "Your practice language could not be changed. Check that the app is running and try again."; control keeps the previous language |
| Catalogue failed | popup shows `role="alert"` "Practice languages could not be loaded. Reload the page to try again." |
| Style | card: `--color-surface`, `--radius-lg`, `--shadow-md`, border `--color-border`; options ≥ 44px tall; selected option uses the selected-card treatment from the design system |

## `LanguageFlag`

- `<span class="fi fi-{flag}" aria-hidden="true">`, 4:3, 1.25em wide, `--radius-sm` corners, 1px
  `--color-border` outline. Renders nothing for an empty `flag`.
- Used by the header control, the switcher options, the Settings practice-language cards, and
  `ConversationLanguageTag`.

## Settings practice-language choice

- Each radio card label shows `LanguageFlag` before the name; the radio's accessible name stays the
  language name (`getByRole('radio', { name: 'German' })` keeps working).
- When the language is switched from the header while Settings is open, the checked radio follows,
  and other unsaved fields keep their values.

## Home

- No `<header>` of its own; the line "Practising … · Change in Settings" is gone. Nav pills, today's
  scenario and the custom scenario are unchanged.

## Conversation and episode headers

- `ConversationLanguageTag` shows `LanguageFlag` before the name; text read by screen readers stays
  "Conversation language: German".
- `EpisodeHeader` shows the same tag for the episode's language under the show title.
