---

description: "Task list for the Language Switcher in the Header (009)"
---

# Tasks: Language Switcher in the Header

**Input**: Design documents from `specs/009-language-switcher-header/`
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md) (R1–R9),
[data-model.md](data-model.md), [contracts/](contracts/) (`api.md`, `ui.md`),
[quickstart.md](quickstart.md)

**Tests**: MANDATORY (Constitution III, TDD). Every test task comes before the implementation it
specifies and must be seen to FAIL first. There are two exceptions. T014 pins existing `PUT /api/settings`
behaviour and must PASS at once. The flag backfill (T050–T054) has a transitional step that is
explained where it happens. Frontend API calls are mocked at `services/api.ts` in Vitest and with
`page.route()` in Playwright. Backend storage is a SQLite test session.

**Organization**: Tasks are grouped by user story in priority order: US1 (header and switch), then US2
(grouping), then US3 (flags). The plan's delivery order (plan.md § "Phase 1", steps 1–7) is kept
inside each story: the backend part of a story comes before its UI. Plan step 1 (flag data) is in US3
and step 2 (`has_activity`) is in US2, because the plan says "US1 can ship with names only". So the
MVP needs neither.

| Phase | Story | Priority | Delivers |
|---|---|---|---|
| 1 | — | — | `flag-icons` installed, stylesheet imported, baseline green |
| 2 | — | — | shared language state on TanStack Query, the switch mutation |
| 3 | US1: see and switch the language from the header | P1 🎯 MVP | `AppLayout`/`AppHeader`, `LanguageSwitcher` (flat list), Home line removed, Settings follows |
| 4 | US2: languages being learned come first | P2 | `PractisedLanguages`, `has_activity`, `groupLanguages`, grouped listbox |
| 5 | US3: every language with its flag | P3 | `flag` language data through the kit, `flag` in the API, `LanguageFlag` everywhere |
| 6 | — | — | docs, quickstart walkthrough, accessibility and validation record |

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1–US3, from spec.md
- Paths are from the repository root. `kit` means `.claude/skills/language-kit/kit.sh`.

## Conventions every task follows

- Functions ≤ 20 lines (Constitution I). The only exceptions are the four long pages in plan.md §
  Complexity Tracking (`Home`, `Flashcards`, `FlashcardDecks`, `Chat`), and each of them only loses or
  gains the single element named in its task. `backend/tests/unit/test_function_length.py` must stay
  green.
- No magic strings: user-visible messages, query keys, ARIA labels and the narrow-screen breakpoint
  are named constants.
- Design-system tokens only (`docs/design-system.md`): no hex, `--radius-lg` cards, `--shadow-md`,
  `--color-text` for control text, `--color-text-muted` for group headings. Touch targets ≥ 44px.
- Module boundaries: `routers/settings.py` imports only the `app.practice_languages` package root;
  the flashcards module is reached only from `services/factory.py`. The kit reaches the app only
  through package roots. App code never hard-codes a language code; `tests/unit/test_no_language_literals.py`
  enforces this.
- The language data files (`backend/app/language_data/languages/*.toml`) are written by `kit`
  only, never by hand (CLAUDE.md, "Per-language data").
- Python runs through `backend/.venv` only. Frontend tests that render anything calling
  `usePracticeLanguages` wrap it in `queryWrapper()` from
  `frontend/src/hooks/podcasts/queryWrapper.test.utils.tsx`.
- Every frontend task ends with `npm test` and `npm run lint` green. Every phase checkpoint also needs
  `npm run test:e2e` green (CLAUDE.md, "Frontend E2E Testing").

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: the flag image set is installed (US3 and the kit's `FlagShipped` rule read it), and the
starting point is known to be green.

- [ ] T001 Add `"flag-icons": "7.5.0"` (exact pin, MIT, research R1) to `dependencies` in `frontend/package.json`; run `cd frontend && npm install`; confirm `frontend/node_modules/flag-icons/flags/4x3/es.svg`, `de.svg` and `it.svg` exist and that `frontend/package-lock.json` changed
- [ ] T002 Import `'flag-icons/css/flag-icons.min.css'` in `frontend/src/main.tsx` before `'./index.css'`, so the app's styles win when both set a property; run `cd frontend && npm run build` and confirm Vite resolves the flag SVG URLs with no error
- [ ] T003 [P] Record the baseline: `cd backend && .venv/bin/pytest`, `cd frontend && npm test && npm run lint && npm run test:e2e`. All must pass before Phase 2. Note any failure that exists before this feature in `specs/009-language-switcher-header/validation.md`, so it is not blamed on this work

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: one shared, cached practice language that every screen reads, and the mutation that
switches it (research R5). Every story's UI depends on this.

**⚠️ CRITICAL**: no user-story work starts until this phase's checkpoint passes.

### Tests (write first, see them fail)

- [ ] T004 Rewrite `frontend/src/hooks/usePracticeLanguages.test.ts` so each `renderHook` gets `queryWrapper()`. Keep every existing assertion: the same return shape (`languages`, `current`, `nameOf`, `isLoading`, `error`), `nameOf` falling back to the code, and the load error "Practice languages could not be loaded. Reload the page to try again." when either request fails. Add `two readers in one query client see the same current language after the settings cache changes` (render two hooks under one wrapper and call `client.setQueryData(['settings'], {...settings, target_language: 'de'})`; both report German) and `requests the catalogue and the settings once for many readers`
- [ ] T005 [P] Write `frontend/src/hooks/useSwitchPracticeLanguage.test.ts` with `queryWrapper()` and a mocked `services/api`. It covers:
  - `sends only the target language`: `api.updateSettings` is called with exactly `{ target_language: 'de' }`.
  - `writes the saved settings into the settings cache`: after success, `usePracticeLanguages().current` in the same client is German, with no new `api.getSettings` call.
  - `invalidates every other query`: seed `['practice-languages']`, `['podcasts', 'catalogue']` and `['flashcards', 'words', 'es']`; all three are invalidated and `['settings']` is not.
  - `reports that it is switching while the request is pending`.
  - `on failure keeps the previous language and exposes the message "Your practice language could not be changed. Check that the app is running and try again."`.
  - `reset clears the error`.

### Implementation

- [ ] T006 Rewrite `frontend/src/hooks/usePracticeLanguages.ts` on two `useQuery` calls. Export the keys as named constants: `PRACTICE_LANGUAGES_QUERY_KEY = ['practice-languages']` and `SETTINGS_QUERY_KEY = ['settings']`. Keep the exported `PracticeLanguagesState` shape and the `LOAD_ERROR` text unchanged, and delete `useLoadedLanguages`, `loadLanguages`, `LOADING` and `FAILED`. The hook stays ≤ 20 lines (≈ 14, plan § Function-length plan). T004 goes green
- [ ] T007 Make the existing tests that render a `usePracticeLanguages` caller pass again by wrapping them in `queryWrapper()`, with no assertion changed. Callers are `useSettingsForm`, `useConversationLanguage`, `PracticeLanguageNote`, and `DeckConfigPanel` and `useLanguageQuery` (where they are not mocked). The affected files are at least `frontend/src/pages/Settings.test.tsx` (`renderSettings`), `frontend/src/pages/Chat.test.tsx`, `frontend/src/pages/Home.test.tsx`, `frontend/src/components/chat/useConversationLanguage.test.ts` and `frontend/src/components/home/PracticeLanguageNote.test.tsx`. Find the rest by running `cd frontend && npm test`
- [ ] T008 Create `frontend/src/hooks/useSwitchPracticeLanguage.ts`: a `useMutation` over `api.updateSettings({ target_language })`. `onSuccess` writes the response into `SETTINGS_QUERY_KEY` and then calls `queryClient.invalidateQueries({ predicate })`, where the predicate skips only the settings key. It returns `{ switchTo(languageId), isSwitching, error, reset }`, with `error` being the named constant `SWITCH_FAILED_MESSAGE` or `null`. Every function ≤ 20 lines. T005 goes green

**Checkpoint**: `npm test` and `npm run test:e2e` are green with no visible change. Every screen now reads
one shared practice language.

---

## Phase 3: User Story 1 — See and switch the practice language from the header (Priority: P1) 🎯 MVP

**Goal**: every top-level screen has a shared header with the current language. One choice in its
switcher saves a new practice language with no Save step. The Home line is gone, and Settings follows
the switch.

**Independent Test**: with Spanish and German catalogued, open Home and read "Spanish" in the header.
Switch to German from the header, then confirm three things: the header, the saved setting (after a
reload, and on Settings) and the next new conversation all use German, with no visit to Settings.
Languages appear as one flat list in catalogue order, with no flags yet.

### Tests for User Story 1 (MANDATORY — write before implementation)

- [ ] T009 [P] [US1] Write `frontend/src/components/language/useListboxKeys.test.ts` for a hook over `(optionIds, activeId)`:
  - ↓ and ↑ move to the next and previous option and do not wrap at either end.
  - Home and End jump to the first and last option.
  - Enter and Space choose the active option.
  - Escape closes.
  - Any other key is ignored and not `preventDefault`ed.
- [ ] T010 [P] [US1] Write `frontend/src/components/language/LanguageSwitcher.test.tsx` (`queryWrapper()`, mocked `services/api`). It asserts contracts/ui.md § "Language control" and § "Switcher":
  - The button is named `Practice language: Spanish`, with `aria-haspopup="listbox"` and `aria-expanded` going `false` → `true`.
  - Opening moves focus to a `listbox` named `Practice language`, and its `aria-activedescendant` is the Spanish option.
  - Options are named by `display_name` only, and Spanish has `aria-selected="true"`.
  - Choosing German calls `updateSettings` with `{ target_language: 'de' }`. The popup then closes, the button reads `Practice language: German`, and focus returns to the button.
  - Choosing Spanish (the current language) closes the popup and sends no request.
  - Escape, and a pointer-down outside the popup, each close it with no request and return focus to the button.
  - While saving, the button has `aria-busy="true"` and still shows Spanish.
  - A failed save leaves the popup open with `role="alert"` "Your practice language could not be changed. Check that the app is running and try again.", and the button stays on Spanish.
  - While loading, the button is named `Practice language` and is disabled.
  - When the catalogue fails to load, the button is named `Practice language` and is enabled, and opening it shows `role="alert"` "Practice languages could not be loaded. Reload the page to try again.".
  - An unknown saved code `pt` gives the name `Practice language: pt`.
- [ ] T011 [P] [US1] Write `frontend/src/components/layout/AppHeader.test.tsx`. It checks four things:
  - Exactly one `banner` landmark holds, in order, a link "Open Language" to `/`, the language control and the theme toggle.
  - The toggle is named "Switch to dark mode" or "Switch to light mode" and flips `data-theme` on `<html>`.
  - The banner has `--color-surface` and a bottom border.
  - Move the theme-toggle tests from `frontend/src/pages/Home.test.tsx` (`describe('Home page — theme toggle')`) here.
- [ ] T012 [P] [US1] Write `frontend/src/App.test.tsx`. Stub every page module with `vi.mock('./pages/<Page>', ...)` as a component rendering its own name, use `MemoryRouter` and `queryWrapper()`, and parametrise over routes:
  - The seven top-level routes (`/`, `/podcasts`, `/history`, `/flashcards`, `/flashcards/decks`, `/flashcards/analytics`, `/settings`) each render one `banner` with a `Practice language…` button, plus the page.
  - `/chat/1`, `/podcasts/setup`, `/podcasts/episodes/1`, `/flashcards/practice/1` and `/flashcards/summary/1` render no `Practice language…` button (FR-006, research R6).
- [ ] T013 [P] [US1] Add to `frontend/src/pages/Settings.test.tsx` the test `switching from the header updates the practice-language radio and keeps other unsaved edits` (FR-019, edge case "Unsaved Settings changes"). Render Settings in a `queryWrapper()` client and change Correction Feedback to Strict without saving. Then `client.setQueryData(['settings'], {...settings, target_language: 'de'})`. The German radio is now checked, the voice list shows German voices, Correction Feedback is still Strict, and `updateSettings` was not called
- [ ] T014 [P] [US1] Add a contract test to `backend/tests/contract/test_practice_languages_api.py`: `test_put_with_only_the_language_returns_its_remembered_voice_and_keeps_the_others`. Store a German voice choice (`de_DE-kerstin-low`) and a Spanish one, then `PUT /api/settings {"target_language": "de"}`. The response has `tts_voice == "de_DE-kerstin-low"`, and the stored Spanish choice is unchanged (contracts/api.md § PUT, research R4). This pins existing behaviour, so it is expected to PASS at once. If it fails, stop: R4's assumption is wrong
- [ ] T015 [P] [US1] Add to `frontend/e2e/fixtures.ts` a helper `mockLanguageSwitchApis(page, { languages, current, failSwitch? })`. It serves `GET /api/settings/practice-languages` and `GET /api/settings` from mutable state. `PUT /api/settings` records each request body, updates `current` and returns the settings, or answers 503 when `failSwitch` is set. It returns `{ putBodies }`
- [ ] T016 [US1] Write `frontend/e2e/language-switcher.spec.ts`, `test.describe('Language switcher — header (US1)')`, using T015. Cover:
  - Home shows the banner control `Practice language: Spanish` and no text "Practising".
  - Opening it and choosing German sends exactly one PUT, with body `{"target_language":"de"}`. The control then reads German within 1 s (SC-005).
  - After a reload the control still reads German, and on `/settings` the German radio is checked.
  - Escape closes with no PUT, and focus is on the control.
  - A click outside closes with no PUT.
  - Choosing the current language sends no PUT.
  - The keyboard-only flow (Tab to the control, Enter, ↓, Enter) switches the language.
  - A failed save shows the alert inside the popup, and the control keeps Spanish (FR-008).
  - Each of the seven top-level routes has exactly one `banner` and the control (FR-001, SC-002).
  - `/chat/:id`, `/podcasts/setup` and `/podcasts/episodes/:id` have no `Practice language…` button (FR-006).
  - On `/flashcards`, switching to German refetches the word list with `language=de`.
  - At a 360px-wide viewport the language name is not visible, and the control's accessible name is still `Practice language: Spanish`. The open popup's bounding box lies inside the viewport, with no horizontal page scroll (Constitution IV, mobile-first).
  - The control's bounding box is at least 44×44px (FR-018).
  - Switching to German when German's mocked entry has `is_voice_installed: false` and a `voice_unavailable_message` still saves (one PUT) and the control reads German. A German conversation then shows the existing voice-unavailable notice and requests no audio in another language's voice (spec edge case "Voice not installed").
- [ ] T017 [P] [US1] Update the existing e2e specs that the header move breaks, and only those:
  - In `frontend/e2e/home.spec.ts`, `displays Open Language heading` asserts the banner link "Open Language" instead of a page heading.
  - In `frontend/e2e/practice-language.spec.ts`, `Practice language — Home` / `names the practice language` asserts the header control `Practice language: German` instead of the Home line.
  - Confirm `frontend/e2e/dark-mode.spec.ts` (`home page shows theme toggle button` / `…switches between light and dark`) passes unchanged with the toggle in `AppHeader`.

### Implementation for User Story 1

- [ ] T018 [P] [US1] Create `frontend/src/components/language/useListboxKeys.ts`, a `keydown` handler from `(optionIds, activeId, { onMove, onChoose, onClose })`. The keys come from a named constant map. T009 goes green
- [ ] T019 [US1] Create `frontend/src/components/language/LanguageListbox.tsx`, a `role="listbox"` named `Practice language`. It renders one flat list of `role="option"` elements, each with a stable `id` (`language-option-{language_id}`), name = `display_name`, `aria-selected` on the current option, and a decorative check mark (`aria-hidden`). It takes `aria-activedescendant` and the keyboard handler from `useListboxKeys`, and options are ≥ 44px tall. Its props are `languages`, `currentId`, `onChoose`, `onClose` and `error` (an optional `role="alert"` message above the options)
- [ ] T020 [US1] Create `frontend/src/components/language/LanguageSwitcher.tsx`. It reads `usePracticeLanguages()` and `useSwitchPracticeLanguage()` and is laid out as a button plus a popup containing `LanguageListbox`:
  - Button: `aria-haspopup="listbox"`, `aria-expanded`, `aria-busy` while switching, and the name from a pure `controlLabel(current, savedId, isLoading)`. It is disabled only while loading.
  - Choosing: the current language just closes the popup. Another language calls `switchTo`, then closes and refocuses the button on success.
  - Dismissing: a pointer-down outside the popup and Escape close it, call `reset()` and refocus the button. Put the outside-pointer logic in a small `useDismissOnOutsidePointer(ref, onDismiss)` in `frontend/src/components/language/useDismissOnOutsidePointer.ts`.
  - Popup style: `--color-surface`, `--radius-lg`, `--shadow-md`, a `--color-border` border, and absolute position under the button.

  Every function ≤ 20 lines. T010 goes green
- [ ] T021 [US1] Add the language control styles to `frontend/src/index.css`, tokens only:
  - `.language-control`: ≥ 44×44px, text `--color-text`, hover and focus as `.nav-pill`.
  - `.language-control__name`: visually hidden below the named breakpoint `400px`.
  - `.language-listbox` and `.language-option`, with the selected option using the design system's selected-card treatment.
  - A group-heading class (`--color-text-muted`, uppercase label style) for US2.
- [ ] T022 [US1] Create `frontend/src/components/layout/AppHeader.tsx` (a `<header>` 56px high and sticky, with `--color-surface` and a bottom `--color-border`). It holds `<Link to="/">Open Language</Link>`, `<LanguageSwitcher />`, and the theme toggle moved unchanged from `frontend/src/pages/Home.tsx` (its `useTheme` usage and labels). Also create `frontend/src/components/layout/AppLayout.tsx`, which renders `<AppHeader />` and `<Outlet />`. T011 goes green
- [ ] T023 [US1] In `frontend/src/App.tsx`, nest the seven top-level routes under `<Route element={<AppLayout />}>`. Leave `/chat/:conversationId`, `/podcasts/setup`, `/podcasts/episodes/:conversationId`, `/flashcards/practice/:sessionId`, `/flashcards/summary/:sessionId` and the `*` redirect outside it. `App` stays ≤ 20 lines. T012 goes green
- [ ] T024 [US1] In `frontend/src/pages/Home.tsx`, delete the page's `<header>` (now `AppHeader`), the `<PracticeLanguageNote />` element and import, and the now-unused `useTheme`. Make no other change (Complexity Tracking row 1). Then delete `frontend/src/components/home/PracticeLanguageNote.tsx` and `frontend/src/components/home/PracticeLanguageNote.test.tsx`, and remove from `frontend/src/pages/Home.test.tsx` the assertions about the removed header and line (FR-007)
- [ ] T025 [P] [US1] In `frontend/src/pages/Flashcards.tsx` and `frontend/src/pages/FlashcardDecks.tsx`, change the page bar's `<header` / `</header>` to `<div` / `</div>`. Change nothing else (Complexity Tracking row 2), so `AppHeader` is the screen's only `banner`
- [ ] T026 [US1] In `frontend/src/components/settings/useSettingsForm.ts`, add `useFollowPracticeLanguage(setValues, current)`: an effect that, when the shared `current?.language_id` changes after the first load, sets only `values.practiceLanguage` and `values.ttsVoice`, both from the saved settings in the `['settings']` cache (`target_language` and `tts_voice`, which the switch's `PUT` response already resolves to that language's remembered voice, research R4), and keeps every other field. It never reads `selected_voice` from the catalogue, which is stale until it is refetched. `useSettingsForm` reaches ≈ 13 lines. T013 goes green
- [ ] T027 [US1] Run `cd backend && .venv/bin/pytest tests/contract/test_practice_languages_api.py` and `cd frontend && npm test && npm run lint && npm run test:e2e`. T014, T016 and T017 must be green, along with every existing spec. US1 acceptance 3 (the next conversation uses the new language) is the existing backend behaviour pinned by `backend/tests/integration/practice_languages/test_conversation_language.py::test_a_new_conversation_is_german`, which must stay green

**Checkpoint**: US1 is shippable. The header switch works on every top-level screen, with names only and
a flat list.

---

## Phase 4: User Story 2 — Languages being learned come first (Priority: P2)

**Goal**: the switcher groups languages under **My languages** (current, then practised, in catalogue
order) and **Start a new language** (the rest), from a server-reported `has_activity` (research R3).

**Independent Test**: with conversations or decks in Spanish and German only, open the switcher.
Spanish and German are under My languages and Italian is under Start a new language. Once an Italian
conversation exists, Italian is under My languages.

### Tests for User Story 2 (MANDATORY — write before implementation)

- [ ] T028 [P] [US2] In `backend/tests/unit/practice_languages/test_catalog.py`, update `test_the_package_exports_exactly_its_public_interface` so `__all__` includes `"PractisedLanguages"`
- [ ] T029 [P] [US2] In `backend/tests/unit/services/test_factory.py`, add tests for the factory's `PractisedLanguages` implementation, built over a SQLite test session with `SQLiteStorageProvider` and `SQLiteFlashcardStorageProvider`:
  - `test_practised_languages_is_empty_on_an_empty_database`
  - `test_a_conversation_makes_its_language_practised`
  - `test_a_podcast_episode_conversation_makes_its_language_practised`
  - `test_a_deck_without_a_conversation_makes_its_language_practised`
  - `test_practised_languages_never_includes_a_language_without_activity`
- [ ] T030 [P] [US2] In `backend/tests/contract/test_practice_languages_api.py`, add `"has_activity"` to `ITEM_KEYS`. In the `client` fixture, also override `get_flashcard_storage` with `SQLiteFlashcardStorageProvider` on the same test session, so no test touches the real database. Add the contract tests from contracts/api.md:
  - `test_has_activity_is_false_for_every_language_on_an_empty_database`
  - `test_a_german_conversation_marks_only_german_active`
  - `test_an_italian_podcast_episode_marks_italian_active` (a `conversations` row in `it`)
  - `test_a_german_deck_without_a_conversation_marks_german_active`
  - `test_the_current_language_without_activity_is_not_active`
- [ ] T031 [P] [US2] Write `frontend/src/components/language/groupLanguages.test.ts` for `groupLanguages(languages, currentId) -> { mine, others }` (data-model.md § Language groups). Cover:
  - The current language comes first in `mine` even when it is last in the catalogue.
  - Practised languages follow it in catalogue order, and `others` keeps catalogue order.
  - A current language without activity is in `mine`.
  - On a fresh install (no activity), `mine` holds only the current language.
  - When every language is practised, `others` is empty.
  - An unknown `currentId` puts nothing first and groups by `has_activity`.
  - A catalogue of one language puts it alone in `mine` and leaves `others` empty.
  - **SC-003, exhaustive**: for 3 languages, every one of the 8 activity combinations × 3 current languages (24 cases) puts every practised or current language before every other one.
- [ ] T032 [P] [US2] Extend `frontend/src/components/language/LanguageSwitcher.test.tsx` with grouped behaviour:
  - Two `role="group"` elements are named "My languages" and "Start a new language" through `aria-labelledby` on their visible headings.
  - An empty group is not rendered: with every language practised there is no "Start a new language" group.
  - With one catalogued language, the listbox holds that one option under My languages and no other group (spec edge case "Only one catalogued language").
  - ↓ from the last option of My languages moves to the first of Start a new language.
  - Choosing a language from Start a new language sends the same `{ target_language }` PUT as any switch.
- [ ] T033 [US2] Add `has_activity` to every practice-language mock in `frontend/e2e/fixtures.ts`: `SPANISH_LANGUAGE` `true`, the others `false`, so the existing specs keep their meaning. Add a helper `languagesWithActivity(codes: string[])`. Then add `test.describe('Language switcher — My languages first (US2)')` to `frontend/e2e/language-switcher.spec.ts`:
  - es+de practised, current es: My languages is Spanish ✓ then German, and Start a new language is Italian.
  - Current it with no activity: Italian is under My languages and selected.
  - Fresh install: only the current language is under My languages.
  - Everything practised: no "Start a new language" group.
  - After a switch, `GET /api/settings/practice-languages` is requested again, so a changed `has_activity` shows (FR-012).

### Implementation for User Story 2

- [ ] T034 [US2] Create `backend/app/practice_languages/activity.py` with `class PractisedLanguages(Protocol)` holding one method, `codes(self) -> frozenset[str]`, and a one-line docstring: the languages the learner has a conversation, podcast episode or flashcard deck in. Export it from `backend/app/practice_languages/__init__.py` (import and `__all__`). T028 goes green
- [ ] T035 [US2] In `backend/app/services/factory.py`, add `_StoredPractisedLanguages(PractisedLanguages)`, built from a `StorageProvider` and a `FlashcardStorageProvider`. Its `codes()` returns the distinct `target_language` of `list_conversations()`, plus each code in `PRACTICE_LANGUAGES` for which `list_decks(language=code)` is non-empty. Also add `get_practised_languages(storage = Depends(get_storage), flashcards = Depends(get_flashcard_storage)) -> PractisedLanguages`. Neither storage ABC changes. T029 goes green
- [ ] T036 [US2] In `backend/app/routers/settings.py`:
  - Add `has_activity: bool` to `PracticeLanguageResponse`.
  - Extract `_voice_status(language, app_settings, installation)`, which returns the `selected_voice` / `is_voice_installed` / `voice_unavailable_message` values (≈ 9 lines).
  - Give `_language_response` a `practised: frozenset[str]` parameter and set `has_activity=language.code in practised` (≈ 14 lines).
  - `get_practice_languages_endpoint` gains `practised: PractisedLanguages = Depends(get_practised_languages)` and calls `.codes()` once.

  Import `PractisedLanguages` from the `app.practice_languages` root only. T030 goes green, and `tests/unit/test_module_boundaries.py` and `tests/unit/test_function_length.py` stay green
- [ ] T037 [P] [US2] Add `has_activity: boolean` to `PracticeLanguageOption` in `frontend/src/services/api.ts`, and add the field to every typed `PracticeLanguageOption` literal in Vitest files (for example the mocks in `frontend/src/components/flashcards/DeckConfigPanel.test.tsx` and `frontend/src/pages/Flashcards*.test.tsx`). Find them with `npx tsc -b`
- [ ] T038 [US2] Create `frontend/src/components/language/groupLanguages.ts`, a pure function with no React. T031 goes green
- [ ] T039 [US2] In `frontend/src/components/language/LanguageListbox.tsx`, render `groupLanguages(languages, currentId)` as up to two `role="group"` elements. Each is labelled by a visible heading (`MY_LANGUAGES_HEADING = 'My languages'`, `NEW_LANGUAGES_HEADING = 'Start a new language'`), and an empty group is not rendered (FR-011). Pass `useListboxKeys` the flat order `[...mine, ...others]`. Extract a `LanguageGroup` component so each function stays ≤ 20 lines. T032 and T033 go green
- [ ] T040 [US2] Run `cd backend && .venv/bin/pytest` and `cd frontend && npm test && npm run lint && npm run test:e2e`. All must be green

**Checkpoint**: US1 and US2 both work. The switcher is grouped, and activity comes from the server.

---

## Phase 5: User Story 3 — Every language is shown with its flag (Priority: P3)

**Goal**: each language data file holds a kit-managed `flag` (research R2). The API returns it, and
`LanguageFlag` draws it beside the name in the header, the switcher, Settings, the chat header and the
episode header. It is always decorative.

**Independent Test**: with Spanish, German and Italian catalogued, the header, switcher and Settings
show each name with its flag, and a screen reader reads each name once. A fourth language (mocked `pt`)
shows its flag with no screen changed.

### Tests for the kit and the language data (write first)

- [ ] T041 [P] [US3] In `backend/tests/unit/language_kit/test_workspace.py`, add `test_the_flag_set_sits_in_the_frontend_node_modules`: `Workspace.flags_dir == root / "frontend/node_modules/flag-icons/flags/4x3"`
- [ ] T042 [P] [US3] In `backend/tests/unit/language_kit/test_context.py`, add:
  - `test_flag_codes_are_the_svg_names_of_the_shipped_flag_set`: write `es.svg`, `de.svg` and `gb-wls.svg` under the workspace's `flags_dir`, and `flag_codes == frozenset({"es", "de", "gb-wls"})`.
  - `test_flag_codes_are_absent_without_the_flag_set`: `None` when the directory is missing.
- [ ] T043 [P] [US3] In `backend/tests/unit/language_kit/test_rules_language.py`, add four tests:
  - `test_flag_shipped_passes_a_flag_in_the_set`
  - `test_flag_shipped_refuses_an_unknown_flag_and_names_the_flag_set`: the detail says the flag-icons set has no `zz` and suggests the default voice's region.
  - `test_flag_shipped_reports_nothing_without_the_flag_set` (`flag_codes=None`, as `VoicesInCatalogue` does without a catalogue)
  - `test_flag_shipped_is_an_error`
- [ ] T044 [P] [US3] In `backend/tests/unit/language_kit/test_registry.py`:
  - Add `("flag", R, A, "009")` to `EXPECTED` directly after `("order", R, D, "008")`.
  - Rename `test_the_registry_holds_the_fourteen_requirements_in_order` to `…_fifteen_…`.
  - Add `test_flag_is_required_a_flag_icons_name_and_shipped`: the rules are `Required`, then `MatchesPattern(r"^[a-z]{2}(-[a-z0-9]+)?$")`, then `FlagShipped`, in that order.

  In `backend/tests/unit/language_kit/test_seeded_omissions.py`, add `"flag": "ESP"` to `BROKEN_VALUES`.
- [ ] T045 [P] [US3] In `backend/tests/unit/language_kit/test_prerequisites.py`:
  - Add `test_prereq_stops_when_the_frontend_flag_set_is_missing`: the failure's detail tells the developer to run `npm install` in `frontend/`.
  - In `backend/tests/unit/language_kit/conftest.py`, make `copy_repository()` also create `frontend/node_modules/flag-icons/flags/4x3/` with an SVG for each language it copies (the prerequisite only needs the directory to exist; `FlagShipped` needs the copied languages' flags). `scaffold` calls the same prerequisites (`commands/scaffold.py`), so every kit test that scaffolds, not only `test_prerequisites.py`, needs the flag set. The new test removes that directory.

### Implementation for the kit (registry, rule, context)

- [ ] T046 [US3] In `backend/language_kit/workspace.py`, add `FLAGS_DIR = Path("frontend/node_modules/flag-icons/flags/4x3")` and a `Workspace.flags_dir` property. In `backend/language_kit/context.py`, add `RuleContext.flag_codes: frozenset[str] | None = None`, plus `_shipped_flags(workspace) -> frozenset[str] | None` (the SVG stems, or `None` without the directory), called from `gather_rule_context` (≈ 9 lines). T041 and T042 go green
- [ ] T047 [US3] Add `class FlagShipped(Rule)` to `backend/language_kit/rules.py`. With `context.flag_codes` set to `None` it returns `[]`; otherwise a value not in the set is an error whose detail names the flag set and the hint "usually the region of the default voice", and `describe()` returns "a flag the frontend ships (flag-icons)". T043 goes green
- [ ] T048 [US3] In `backend/language_kit/registry.py`, add after the `order` requirement `Requirement("flag", _R, _AGENT, "009", "The flag shown beside the language's name: a flag-icons name, a lowercase ISO 3166-1 region (es) or region-subdivision (gb-wls); usually the region of the default voice.", (Required(), MatchesPattern(r"^[a-z]{2}(-[a-z0-9]+)?$", "a lowercase region code, optionally -subdivision"), FlagShipped()))`. Then, in `backend/language_kit/prerequisites.py`, add the flag-set check that runs after the code rules: `context.flag_codes is None` is a failure saying `Run "npm install" in frontend/ so the kit can check flags.` T044 and T045 go green, and every other test in `backend/tests/unit/language_kit/` (including `test_scaffold_command.py`) stays green. `tests/unit/language_kit/test_registry_covers_language_data.py` now FAILS, because the requirement has no record field until T049. This is expected

### Language data: record, transitional loader, backfill, strict loader

> The kit imports `app.practice_languages`, which loads every data file with the strict loader when
> it is imported. If the loader requires `flag` before the files have it, the kit cannot start. If
> the files gain `flag` before the loader knows it, the loader refuses the unknown key. So the loader
> accepts `flag` as optional while the kit writes it (T049), and makes it required once all three
> files have it (T053).

- [ ] T049 [US3] Write the test first in `backend/tests/unit/language_data/test_loader.py`: extend `test_a_record_holds_every_value_of_its_file` with `flag = "es"` → `record.flag == "es"`, and see it fail. Then add `flag: str` to `LanguageRecord` in `backend/app/language_data/records.py`, and read it in `_FileReader.language` in `backend/app/language_data/loader.py` (≈ 13 lines). **Transitional**: list `flag` in a temporary `_TRANSITIONAL_OPTIONAL_KEYS = {"flag": ""}` that `_check_table` accepts when absent, with a comment saying T053 removes it. The loader test and `test_registry_covers_language_data.py` go green, and `cd backend && .venv/bin/pytest` is green
- [ ] T050 [US3] Backfill. Confirm `.specify/feature.json` names `specs/009-language-switcher-header`, then run:
  - `kit requirements`: lists `flag` (needed by 009).
  - `kit check --all`: Spanish, German and Italian each FAIL `flag`, and nothing else.
  - `kit backfill --all`: writes `specs/009-language-switcher-header/languages/{es,de,it}/backfill-pack.toml`.
- [ ] T051 [US3] Fill the three backfill packs with `flag = "es"`, `flag = "de"` and `flag = "it"` (data-model.md; the default voices are `es_ES`, `de_DE` and `it_IT`), following the pack's guidance and nothing else (the skill's Rules: never read app source while backfilling). Then run `kit validate <code> --pack specs/009-language-switcher-header/languages/<code>/backfill-pack.toml` for each until it reports `0 errors`
- [ ] T052 [US3] Run `kit apply <code> --pack …` for `es`, `de` and `it`, all three before any `finish` (the skill's backfill step 5). Then confirm three things with `git diff backend/app/language_data/languages/`: each file only gains its `flag` line, the generated-file header comment is intact, and no evaluation file changed
- [ ] T053 [US3] Make `flag` required. Write the test first: `test_a_missing_flag_names_the_file_and_the_key` in `backend/tests/unit/language_data/test_loader.py`, and see it fail. (The pinned values are extended in T061, because they read `PracticeLanguage`, which carries `flag` only from then.) Then add `"flag": str` to `_LANGUAGE_SCHEMA` and delete `_TRANSITIONAL_OPTIONAL_KEYS` and its handling in `backend/app/language_data/loader.py`. All loader tests go green, and `backend/.venv/bin/python -m app.language_data voice-keys` still loads every file
- [ ] T054 [US3] Run `kit finish <code> --pack specs/009-language-switcher-header/languages/<code>/backfill-pack.toml` for `es`, `de` and `it`, then `kit check --all`: 0 errors for all three. Keep the reports `finish` writes under `specs/009-language-switcher-header/languages/`

### Tests for the API and the UI (write first)

- [ ] T055 [P] [US3] In `backend/tests/unit/practice_languages/test_catalog.py`, add `test_every_language_has_a_flag_from_its_data` (`PRACTICE_LANGUAGES[code].flag == record.flag`, non-empty) and `test_spanish_german_and_italian_flags_are_es_de_it`
- [ ] T056 [P] [US3] In `backend/tests/contract/test_practice_languages_api.py`, add `"flag"` to `ITEM_KEYS` and add `test_every_entry_has_its_language_datas_flag` (non-empty, equal to `PRACTICE_LANGUAGES[code].flag`)
- [ ] T057 [P] [US3] Write `frontend/src/components/language/LanguageFlag.test.tsx`: `flag="de"` renders one element with classes `fi fi-de` and `aria-hidden="true"`, and an empty `flag` renders nothing
- [ ] T058 [P] [US3] Add flag assertions to the existing component tests. In each, the flag element has `aria-hidden` and accessible names do not change:
  - `frontend/src/components/language/LanguageSwitcher.test.tsx`: the button and each option contain `.fi-{flag}`, the names stay `Practice language: Spanish` and `Spanish`, and an unknown saved code shows no flag.
  - `frontend/src/components/settings/PracticeLanguageFieldset.test.tsx`: each card label shows its flag before the name, and `getByRole('radio', { name: 'German' })` still finds the German radio.
  - `frontend/src/components/chat/ConversationLanguageTag.test.tsx`: with `flag="de"`, the flag is drawn before the name, and the text read is still "Conversation language: German".
  - `frontend/src/components/chat/useConversationLanguage.test.ts`: `targetFlag` comes from the catalogue entry, and is `''` for an unknown language.
- [ ] T059 [P] [US3] Create `frontend/src/components/podcasts/EpisodeHeader.test.tsx` (`queryWrapper()`, mocked `services/api` catalogue). An episode with `language: 'it'`, `language_name: 'Italian'` shows, under the show title, the tag "Conversation language: Italian" with an `fi-it` flag, and no `Practice language…` button
- [ ] T060 [US3] Add `flag` (`'es'`, `'de'`, `'it'`) to every language mock in `frontend/e2e/fixtures.ts`, plus a `PORTUGUESE_LANGUAGE` mock with `flag: 'pt'`. Then add `test.describe('Language switcher — flags (US3)')` to `frontend/e2e/language-switcher.spec.ts`:
  - The header control and every switcher option show `.fi-{flag}`, and the options' accessible names are exactly the language names (FR-015).
  - Each Settings practice-language card shows its flag.
  - With Portuguese added to the mocked catalogue, its flag appears in the header (after switching to it), in the switcher and on Settings (SC-004).
  - In light and in dark mode, the control text, the group headings and the option text meet WCAG AA contrast, parametrised over both themes the way `practice-language.spec.ts`'s `every card label meets text contrast in … mode` test is.

  In `frontend/e2e/practice-language.spec.ts`, extend `the header shows German and offers no language control` so the chat header also shows the `fi-de` flag.

### Implementation for User Story 3

- [ ] T061 [US3] Test first: in `backend/tests/unit/language_data/test_pinned_language_values.py`, add `"flag": language.flag` to `_as_plain` and `"flag": "es"` / `"flag": "de"` to the pinned Spanish and German values, and see it fail with T055. Then add `flag: str` to `PracticeLanguage` in `backend/app/practice_languages/catalog.py`, and set `flag=record.flag` in `_practice_language` (≈ 10 lines). T055 and the pinned tests go green
- [ ] T062 [US3] In `backend/app/routers/settings.py`, add `flag: str` to `PracticeLanguageResponse` and set `flag=language.flag` in `_language_response` (≤ 20 lines). T056 goes green
- [ ] T063 [P] [US3] Add `flag: string` to `PracticeLanguageOption` in `frontend/src/services/api.ts`, and add the field to the typed Vitest literals (find them with `npx tsc -b`, as in T037)
- [ ] T064 [US3] Create `frontend/src/components/language/LanguageFlag.tsx`, which renders `<span className={`fi fi-${flag} language-flag`} aria-hidden="true" />` or `null` for an empty flag. In `frontend/src/index.css`, add `.language-flag`: width `1.25em`, 4:3, `border-radius: var(--radius-sm)`, `outline: 1px solid var(--color-border)` with no hex values. T057 goes green
- [ ] T065 [US3] Draw `LanguageFlag` before the name in the button of `frontend/src/components/language/LanguageSwitcher.tsx` (no flag for an unknown saved code) and in each option of `frontend/src/components/language/LanguageListbox.tsx`. In `frontend/src/components/settings/PracticeLanguageFieldset.tsx`, move the option mapping into a `languageOption(language)` helper that adds `LanguageFlag` before the name, which brings the component from 21 to ≈ 17 lines. The LanguageSwitcher and PracticeLanguageFieldset parts of T058 go green
- [ ] T066 [US3] Three changes for the chat header:
  - `frontend/src/components/chat/useConversationLanguage.ts`: add `targetFlag: entry?.flag ?? ''` to `ConversationLanguage`.
  - `frontend/src/components/chat/ConversationLanguageTag.tsx`: add an optional `flag` prop that draws `LanguageFlag` before the name.
  - `frontend/src/pages/Chat.tsx`: pass `flag={language.targetFlag}` at the tag's call site, and change nothing else (Complexity Tracking row 3).

  The remaining parts of T058 go green
- [ ] T067 [US3] In `frontend/src/components/podcasts/EpisodeHeader.tsx`, render `<ConversationLanguageTag name={episode.language_name} flag={…} />` under `PodcastLabel`. The flag comes from `usePracticeLanguages().languages` looked up by `episode.language`. The component stays ≤ 20 lines; T059 goes green
- [ ] T068 [US3] Run `cd backend && .venv/bin/pytest` and `cd frontend && npm test && npm run lint && npm run test:e2e`. T060 and every existing spec must be green

**Checkpoint**: all three stories work independently, and every language shows its flag with no
per-language frontend file.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: docs, the full gates, and the manual validation the constitution requires.

- [ ] T069 [P] Add a "Language control" component pattern to `docs/design-system.md`: the header control, the listbox popup with grouped options, `LanguageFlag` (decorative, outlined), the narrow-screen rule, and the tokens used (contracts/ui.md)
- [ ] T070 [P] Add the 009 entry to `docs/architecture.md`, written like the 008 entry. It covers the `AppLayout` layout route and which screens it excludes; `PractisedLanguages`, implemented in the factory; `has_activity` and `flag` on the catalogue endpoint; the shared TanStack Query language state with invalidate-all after a switch; and `flag` as kit-managed language data
- [ ] T071 [P] Update `CLAUDE.md`. Add 009 to the "Features shipped so far" sentence, add a `009-language-switcher-header` entry at the top of "Recent Changes" in the style of 008's, and add `flag-icons` to "Active Technologies → Frontend"
- [ ] T072 Function-length and boundary gate. `cd backend && .venv/bin/pytest tests/unit/test_function_length.py tests/unit/test_module_boundaries.py tests/unit/test_no_language_literals.py tests/unit/language_kit/test_kit_boundaries.py` must be green. Then measure every new or modified frontend function from plan.md § Function-length plan, and confirm each is ≤ 20 lines except the four Complexity Tracking pages
- [ ] T073 Run quickstart.md § 1: `cd backend && .venv/bin/pytest --cov=app --cov=language_kit` (≥ 90%, zero skipped), `.venv/bin/ruff check . && .venv/bin/black --check .`, and `cd ../frontend && npm run lint && npm test -- --run && npm run test:e2e`. Everything must be green
- [ ] T074 Run quickstart.md § 2 (`kit requirements`, `kit check --all`, `python -m app.language_data voice-keys`) and § 5, the SC-004 dry run. Run `kit scaffold pt --name Portuguese`, then `kit validate pt`, which fails `flag` with `zz` and passes with `pt`. Then `rm -r specs/009-language-switcher-header/languages/pt`, so the dry run is not committed
- [ ] T075 Do the quickstart.md § 3 manual walkthrough (rows 1–12) on the real app (`./run.sh`) and the § 4 accessibility check: keyboard only, Orca, WCAG AA contrast in light and dark, and 44px targets. Record the results, including the SC-005 time from choice to header update, and FR-016 as met by design (SVG images from `flag-icons`, no flag emoji or OS font), with Linux the only platform checked by hand, in `specs/009-language-switcher-header/validation.md` (create it if T003 did not) written like `specs/008-language-onboarding-kit/validation.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none. T001 must finish before T046–T054 (the kit's `FlagShipped` reads the
  installed flag set) and before T064.
- **Foundational (Phase 2)**: depends on Setup and BLOCKS every story. Every story's UI reads
  `usePracticeLanguages` from the shared cache, and US1's switch is `useSwitchPracticeLanguage`.
- **US1 (Phase 3)**: depends only on Phase 2. It is the MVP.
- **US2 (Phase 4)**: its backend half (T028–T030, T034–T036) depends on nothing in US1 and can start
  right after Phase 2. Its frontend half extends US1's `LanguageListbox` and `LanguageSwitcher`
  (T032, T039), so it follows T019–T020.
- **US3 (Phase 5)**: its kit and data half (T041–T054) depends only on T001 and can run beside US1
  and US2. T061–T062 depend on T053. Its UI half extends US1's components (T065) and US2's listbox
  groups, so it follows T039.
- **Polish (Phase 6)**: depends on every story.

### Within User Story 3 (strict order)

`T046 → T047 → T048` (guard red) `→ T049` (transitional loader; guard green) `→ T050 → T051 → T052`
(all three applied) `→ T053` (strict loader) `→ T054` (finish ×3) `→ T061 → T062`.

### Within Each Story

- Tests are written first and seen to fail. T014 is the exception: it pins existing behaviour and is
  meant to pass.
- Backend before the UI that reads it: T036 before T033 and T039 are green, and T062 before T060 is
  green.
- `useListboxKeys` → `LanguageListbox` → `LanguageSwitcher` → `AppHeader`/`AppLayout` → `App`.

### Parallel Opportunities

- Phase 2: T005 alongside T004.
- US1 tests T009–T015 all touch different files. T018 and T025 can run in parallel with other
  implementation tasks.
- US2: the backend tests T028–T030 and the frontend tests T031–T032 run together. T037 runs beside
  T034–T036.
- US3: the kit tests T041–T045 run together, and so do the API and UI tests T055–T059. The kit and
  data chain (T046–T054) can run while US1 or US2 UI work is in progress.
- Polish: T069–T071 run together.

---

## Parallel Example: User Story 1

```bash
# All US1 tests together (different files):
Task: "T009 useListboxKeys.test.ts"
Task: "T010 LanguageSwitcher.test.tsx"
Task: "T011 AppHeader.test.tsx"
Task: "T012 App.test.tsx (layout routes)"
Task: "T013 Settings.test.tsx follows a header switch"
Task: "T014 contract: PUT with only target_language"
Task: "T015 e2e fixtures: mockLanguageSwitchApis"

# Then, independent implementation pieces:
Task: "T018 useListboxKeys.ts"
Task: "T025 Flashcards/FlashcardDecks <header> → <div>"
```

## Parallel Example: User Story 2

```bash
Task: "T028 practice_languages exports PractisedLanguages"
Task: "T029 factory PractisedLanguages tests"
Task: "T030 contract: has_activity"
Task: "T031 groupLanguages.test.ts (incl. SC-003 exhaustive)"
Task: "T032 grouped LanguageSwitcher tests"
```

## Parallel Example: User Story 3

```bash
# Kit tests:
Task: "T041 Workspace.flags_dir"
Task: "T042 RuleContext.flag_codes"
Task: "T043 FlagShipped rule"
Task: "T044 registry + BROKEN_VALUES"
Task: "T045 prereq flag-set check"
# API and UI tests:
Task: "T055 catalogue flag"   Task: "T056 contract flag"
Task: "T057 LanguageFlag"     Task: "T058 flag in existing components"   Task: "T059 EpisodeHeader"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1: Setup (T001–T003).
2. Phase 2: shared language state (T004–T008).
3. Phase 3: US1 (T009–T027).
4. **STOP and VALIDATE** with US1's Independent Test and quickstart rows 1, 3, 4, 5, 7–11. Names
   only, in a flat list.

### Incremental Delivery

1. Setup + Foundational → no visible change, shared state in place.
2. US1 → the header switcher, with the Home line gone (MVP).
3. US2 → My languages first.
4. US3 → flags, through the language kit.
5. Polish → docs, gates, manual walkthrough and validation record.

### Parallel Team Strategy

Once Phase 2 is done: Developer A takes US1 (frontend), Developer B takes US2's backend (T028–T030,
T034–T036), and Developer C takes US3's kit and data chain (T041–T054). Each UI half then merges in
story order (US1 → US2 → US3), because the switcher components are shared.

---

## Notes

- [P] tasks touch different files and depend on no incomplete task.
- Never edit `backend/app/language_data/languages/*.toml` by hand. If T052's diff shows anything
  other than the `flag` line, stop and fix the pack, not the file.
- `_TRANSITIONAL_OPTIONAL_KEYS` (T049) exists only between T049 and T053 and must not survive T053.
- Commit after each task or logical group; the `after_implement` hook commits at the end.
