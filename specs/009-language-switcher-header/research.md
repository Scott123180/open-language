# Research: Language Switcher in the Header

**Feature**: 009-language-switcher-header | **Date**: 2026-10-07

Measured on `009-language-switcher-header` @ `53b52d4`. The Technical Context had no open
unknowns after this research. Each decision below records what was chosen, why, and what was
rejected.

## R1 — How flags are drawn

**Decision**: Ship flags as SVG images from the `flag-icons` npm package (7.5.0, MIT, published
2025-05-29), imported once as its stylesheet in `frontend/src/main.tsx`. A language's flag is drawn
by one component, `LanguageFlag`, as `<span class="fi fi-{flag}" aria-hidden="true">`.

**Rationale**:
- FR-016 requires the same look on Linux, macOS and Windows. Flag emoji are regional-indicator
  pairs that Windows does not render (it shows the two letters), and Linux renders them only when a
  colour emoji font is installed. Images are the only way to meet FR-016.
- The package covers every ISO 3166-1 region plus subdivisions such as `gb-wls` and `es-ct`, so a
  language onboarded later (Welsh, Catalan) has a flag without adding image files (SC-004).
- The stylesheet references each SVG through `background-image`, so a browser fetches only the
  flags on screen. Vite copies the whole set (about 540 small files, ≈3 MB) into `dist/`; for a
  locally run app this costs disk space, not load time. Nothing is fetched from the network at run
  time (Assumptions: no network).
- It needs no colour tokens: a flag is an image, so the design system's "no hard-coded hex" rule
  is unaffected. A 1px `--color-border` outline keeps white-edged flags visible in light mode.

**Alternatives considered**:
- *Emoji flags*: rejected for FR-016 (above).
- *`country-flag-icons` (React components)*: a component per flag means a dynamic lookup imports
  every component into the bundle as JavaScript; heavier than lazily loaded images.
- *Hand-copied SVGs in `frontend/src/assets/flags/`*: every new language would need a frontend file
  added next to its data, which breaks SC-004 ("zero changes to those screens") in spirit and puts
  a second per-language artefact outside the language kit.
- *Backend serves the SVG*: adds an endpoint and bytes to language data for no gain.

## R2 — Where a language's flag is designated

**Decision**: A new required runtime field `flag` in each language data file
(`backend/app/language_data/languages/<code>.toml`): the `flag-icons` name of the flag, which is a
lowercase ISO 3166-1 alpha-2 region (`es`, `de`, `it`) or a region-subdivision (`gb-wls`). It is
added the way the language kit requires (CLAUDE.md, "Per-language data"):

1. `LanguageRecord.flag: str` and the strict loader, test first;
2. a `Requirement("flag", RUNTIME, AGENT, "009", …)` in `backend/language_kit/registry.py` with the
   rules `Required()`, `MatchesPattern(r"^[a-z]{2}(-[a-z0-9]+)?$", …)` and a new `FlagShipped()`;
3. `kit.sh backfill --all`, then one pack per language with `es`, `de`, `it`, finished with
   `kit.sh finish`.

The values match each language's default-voice region (`es_ES`, `de_DE`, `it_IT`), per the spec's
Assumptions. The requirement's description tells the agent "usually the region of the default
voice".

**Rationale**: FR-013 puts the flag with the rest of the language's data, and the kit already
enforces that every language has every required value. The producer is `AGENT` rather than
`DERIVED` because the default voice's region is a good suggestion, not always the right answer: an
English pack whose best voice is `en_GB` may still want `us`, and Catalan voices are `ca_ES` but the
flag is `es-ct`.

**`FlagShipped` rule**: checks that `frontend/node_modules/flag-icons/flags/4x3/{flag}.svg` exists.
`gather_rule_context` reads the set of names once into a new `RuleContext.flag_codes:
frozenset[str] | None`. When the directory is missing, the field is `None` and the rule reports
nothing, as `VoicesInCatalogue` does without a catalogue; `kit.sh prereq` gains a check that says
"run `npm install` in `frontend/`" when it is missing. `kit.sh finish` already runs the frontend
suites, which need `node_modules`, so a real onboarding always has it.

**Alternatives considered**:
- *Derive the flag from the default voice's locale at run time, no new field*: wrong for Catalan and
  any language whose best voice is from a smaller region; and the flag would change silently if the
  default voice changed.
- *A hard-coded ISO 3166 list in `rules.py`*: duplicates what the shipped flag set already knows,
  and would accept a code the package has no image for.

## R3 — What "My languages" is made of, and who computes it

**Decision**: `GET /api/settings/practice-languages` gains `has_activity: bool` per language: true
when the learner has at least one conversation (roleplay or podcast episode, both are
`conversations` rows) or one flashcard deck in that language. The frontend groups the list with one
pure function, `groupLanguages(languages, currentId)`: My languages is the current language first,
then languages with `has_activity` in catalogue order; Start a new language is the rest in catalogue
order (FR-009, FR-010, FR-011).

The backend reads activity through a small protocol declared in the `practice_languages` package:

```python
class PractisedLanguages(Protocol):
    def codes(self) -> frozenset[str]: ...
```

`services/factory.py` implements it from the two existing storage interfaces, with no new query
method on either: the distinct `target_language` of `StorageProvider.list_conversations()`, plus each
catalogued code for which `FlashcardStorageProvider.list_decks(language=code)` is non-empty. The
settings router depends on the protocol through a new `get_practised_languages` dependency.

**Rationale**:
- Principle V: the settings router must not import flashcards internals. A protocol in the
  language package, implemented in the factory, is the pattern 007 used for `SpeakerNames` and
  `MessageVoiceLookup`.
- Saved words always come from a conversation, and a practice session always belongs to a deck, so
  conversations plus decks cover every way a learner can have practised a language.
- Keeping "current" out of `has_activity` leaves the server reporting a fact and the client deciding
  presentation. After a switch, the client knows the new current language at once, and the grouping
  is right before the list is refetched.
- Reusing `list_conversations()` avoids changing an ABC. It loads every conversation row (no
  messages); a local learner has hundreds, and the endpoint is called once per screen load. If that
  ever matters, a `conversation_languages()` query can replace it behind the same protocol.

**Alternatives considered**:
- *A new endpoint `GET /api/learning-languages`*: a second request for data that belongs on each
  catalogue entry, and a second cache to invalidate after a switch.
- *A stored "my courses" list*: the spec's Assumptions rule out a separate add/remove step; activity
  is the definition.
- *Counting saved words or practice sessions too*: they never exist without a conversation or deck.

## R4 — How the switch is saved

**Decision**: The switcher sends `PUT /api/settings` with `{ "target_language": "<code>" }` only.
No backend change is needed: `_to_response` already returns the voice remembered for the new
language (`voice_for(target_language, voice_choices)`), and leaving `tts_voice` out keeps every
language's voice choice untouched (FR-004).

**Rationale**: The endpoint already accepts partial updates (`exclude_none`). Sending the voice too,
as Settings does, would need the frontend to look up the new language's remembered voice first, for
nothing.

## R5 — Sharing the practice language across the app

**Decision**: Move `usePracticeLanguages` onto TanStack Query (already used by Flashcards and
Podcasts): queries `['practice-languages']` and `['settings']`. Its return shape is unchanged, so its
five callers do not change. A new `useSwitchPracticeLanguage()` mutation saves the switch, writes
the returned settings into the `['settings']` cache (the header updates from that, SC-005), then
invalidates every query except `['settings']`. That refetches the catalogue (`has_activity`), the
podcast catalogue (its key has no language), and the Flashcards queries.

**Rationale**:
- Today each `usePracticeLanguages()` call keeps its own `useState` copy, loaded once. A switch made
  in the header would not reach a Flashcards list or the Settings form already on screen. One query
  cache makes every reader see the same language.
- Invalidating every query matches the spec's edge case "that screen shows the new language's
  content after the switch, as if it had been opened fresh", without the switcher knowing which
  screens hold per-language data. Flashcards keys already include the language; the podcast catalogue
  key does not.
- The UI shows the new language when the save succeeds, not before. FR-008 requires the previous
  language to stay visible on a failure; waiting for a sub-second local request is simpler than an
  optimistic update with rollback. While saving, the control shows a busy state (Principle IV,
  immediate feedback).

**Settings form (edge case "Unsaved Settings changes")**: `useSettingsForm` copies stored settings
into local form state once. It gains one effect: when the shared current language changes, the form's
`practiceLanguage` (and the voice list that follows it) takes the new value, and every other unsaved
field is kept. Settings's own Save keeps working as today.

**Alternatives considered**:
- *A React context provider for the language*: duplicates what the query cache already provides.
- *Invalidating only named keys*: the switcher would need to know every per-language screen, which
  breaks Open/Closed as screens are added.

## R6 — One header for the top-level screens

**Decision**: A layout route in `App.tsx`. `AppLayout` renders `AppHeader` and an `<Outlet />` for
the top-level routes: `/`, `/podcasts`, `/podcasts/setup`, `/history`, `/flashcards`,
`/flashcards/decks`, `/flashcards/analytics`, `/settings`. `AppHeader` holds the app name (a link
home), the `LanguageSwitcher`, and the theme toggle that today sits only in Home's header. The task
screens — `/chat/:id`, `/podcasts/episodes/:id`, `/flashcards/practice/:id`,
`/flashcards/summary/:id` — stay outside the layout, keep their headers, and so never offer the
switcher (FR-006).

Home loses its own `<header>` (now `AppHeader`) and `PracticeLanguageNote` (FR-007, the component
and its test are deleted). Flashcards and FlashcardDecks render their page bars as `<div>` instead of
`<header>`, so the app keeps one `banner` landmark per screen.

**Rationale**: FR-001 needs the same control on eight screens; one layout is one place to change. The
theme toggle moves into the shared header because Home's header is the only place it lives today, and
removing Home's header must not remove it.

**Alternatives considered**:
- *Adding the switcher to each page's own header*: eight edits to long page components, and History,
  Settings and the podcast pages have no header to add it to.
- *Wrapping every route, including task screens*: the switcher would need a "read-only" mode and
  each task screen would show two bars.

## R7 — The switcher's interaction and accessibility pattern

**Decision**: The WAI-ARIA "listbox popup" pattern.
- The header control is a `<button aria-haspopup="listbox" aria-expanded>` whose accessible name is
  "Practice language: Spanish" (FR-017). It shows the flag and the name; below 400px wide, the name
  is visually hidden and stays in the accessible name (edge case "Narrow screens").
- The popup is a `role="listbox"` containing two `role="group"` elements, each labelled by its
  visible heading ("My languages", "Start a new language"). Each language is a `role="option"`, and
  the current one has `aria-selected="true"` and a check mark.
- Focus moves into the listbox on open, onto the current language. Up and Down move through the
  options across both groups, Home and End jump to the first and last, Enter or Space chooses,
  Escape closes. A click outside also closes. Closing returns focus to the button (FR-005, FR-017).
  The active option is tracked with `aria-activedescendant`.
- Touch targets are at least 44px tall (FR-018, design system). The popup is a card: `--radius-lg`,
  `--shadow-md`, `--color-surface`; text uses `--color-text`, and group headings use
  `--color-text-muted`, as the design system's section labels do.

**Rationale**: Choosing one value from a list is what a listbox is for. A `menu` would announce
actions, not a selection with a current value. A native `<select>` cannot show flag images or group
headings in its options on every platform.

## R8 — Read-only language in a conversation and an episode (FR-006)

**Decision**: `ConversationLanguageTag` gains an optional `flag` prop and draws `LanguageFlag` before
the name. Chat passes `flag` from `useConversationLanguage`, which adds `targetFlag` from the
catalogue entry it already looks up. `EpisodeHeader` adds the same tag under the show title, from
`episode.language_name` and the catalogue entry for `episode.language`.

**Rationale**: The tag already exists, is read-only by design, and carries a visually hidden
"Conversation language:" prefix for screen readers. The flag is decorative (FR-015).

## R9 — Unknown or missing data

- *Saved language not in the catalogue*: `usePracticeLanguages().current` is `null`; `nameOf()`
  already falls back to the code. The header shows the code with no flag and the switcher lists the
  catalogue (spec edge case).
- *Catalogue failed to load*: the header shows "Language" with no flag and the switcher shows the
  existing load error, "Practice languages could not be loaded. Reload the page to try again."
- *Switch failed*: the switcher stays open, shows "Your practice language could not be changed.
  Check that the app is running and try again." in an `ErrorBanner` style alert inside the popup, and
  the header keeps the previous language (FR-008).
- *Chosen language's voice missing*: the switch goes through. The header shows the language as
  usual; the existing per-language `voice_unavailable_message` already appears where audio is used,
  and no fallback voice is used (spec edge case).
