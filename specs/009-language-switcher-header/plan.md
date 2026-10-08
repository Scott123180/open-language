# Implementation Plan: Language Switcher in the Header

**Branch**: `009-language-switcher-header` | **Date**: 2026-10-07 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/009-language-switcher-header/spec.md`

## Summary

The current practice language moves from a muted line on Home into a shared header on every
top-level screen. The header shows the language's flag and name, and selecting it opens a
listbox: **My languages** (the current language, then every language the learner has a
conversation, podcast episode or flashcard deck in) above **Start a new language**. One choice
saves the language. No Save button and no visit to Settings.

Technically:
- **Flags** are `flag-icons` SVGs (research R1). Each language data file gains a required `flag`,
  added through the language kit: a record field, a registry `Requirement` with a new `FlagShipped`
  rule, and `kit.sh backfill` for Spanish, German and Italian (R2).
- **Activity** is one new boolean, `has_activity`, on each `GET /api/settings/practice-languages`
  entry. It is computed through a `PractisedLanguages` protocol that the factory implements from
  the existing conversation and flashcard storage interfaces (R3).
- **The switch** is the existing `PUT /api/settings {target_language}` (R4). `usePracticeLanguages`
  moves onto TanStack Query so every screen sees the same language. After a switch every other query
  is invalidated, so per-language screens reload (R5).
- **The header** is a layout route around the seven top-level routes. Task screens (chat, episode
  setup, episode, practice, summary) keep their own headers and never offer the switcher. Chat and episode headers
  show their language read-only with its flag (R6, R8).

No database change, no new endpoint, no AI provider involved.

## Technical Context

**Language/Version**: Python ≥ 3.11 (venv 3.12.3) backend; TypeScript 5.4 / React 18.3 frontend
**Primary Dependencies**: FastAPI, Pydantic, SQLAlchemy 2.0 (unchanged); React Router v6, TanStack
Query v5 (existing); **new**: `flag-icons@7.5.0` (MIT, frontend runtime, SVG flags)
**Storage**: SQLite, unchanged (no table, no column). Language data TOML files gain `flag`
**Testing**: pytest + pytest-cov (unit, contract, language-kit); Vitest + Testing Library; Playwright
**Target Platform**: Locally run web app on Linux, macOS, Windows desktop browsers
**Project Type**: Web application (`backend/` + `frontend/`)
**Performance Goals**: Header reflects a switch within 1 s on a local install (SC-005)
**Constraints**: No network at run time for flags (R1); same flag rendering on every OS (FR-016);
one `banner` landmark per screen; design-system tokens only
**Scale/Scope**: 3 catalogued languages today, open-ended; 7 top-level screens, 2 task headers

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / gate | Assessment |
|---|---|
| I. Clean Code (≤ 20-line functions, named constants) | **PASS with tracking.** New code is written to the limit. `_language_response` would reach 21 lines, so its voice part is extracted (see Function-length plan). Long page components that change get rows in Complexity Tracking, as 004–007 did |
| II. SOLID | **PASS.** `PractisedLanguages` is a one-method protocol (ISP), implemented in the factory (DIP). Grouping is a pure function. The switcher depends on `usePracticeLanguages` / `useSwitchPracticeLanguage`, not on `api` |
| III. TDD (non-negotiable) | **PASS.** Each task starts with a failing test: loader and registry tests, contract tests for the two new fields, Vitest for `groupLanguages`, `LanguageFlag`, `LanguageSwitcher`, `AppHeader`, `usePracticeLanguages`, and a new Playwright spec, `language-switcher.spec.ts` |
| IV. Simple UI & UX | **PASS.** The header control is secondary to each screen's primary action. Immediate feedback (busy state, error inside the popup), plain-language errors that say what to do, keyboard and screen-reader pattern (R7), 44px targets, light and dark tokens |
| V. Extensibility & compartmentalisation | **PASS.** Settings reads activity through the `practice_languages` package root, never importing flashcards. A new language's flag needs only its data file (SC-004). Invalidating every query means a new per-language screen needs no switcher change |
| VI. Provider independence | **N/A.** No AI capability or provider is touched |
| Per-language data → language-kit requirement in the same change | **PASS.** `flag` gets a `Requirement`, a record field, a loader check and a backfill of all three languages, in this feature (R2) |
| Playwright E2E for all frontend changes | **PASS.** New `frontend/e2e/language-switcher.spec.ts`. `home.spec.ts` and `practice-language.spec.ts` are updated, and the fixtures gain `flag` / `has_activity` |
| Manual accessibility check | **Planned.** quickstart.md § 4 |
| Lint / format | **PASS.** ruff, black, eslint, prettier run in `kit.sh finish` and in the quickstart |

**Initial gate: PASS**, with three Complexity Tracking rows covering four long React pages, each
of which loses or gains a single element.

### Function-length plan (Boy Scout, quality gate)

Measured on `009-language-switcher-header` @ `53b52d4`.

| Function | Today | Change |
|---|---|---|
| `_language_response` ([settings.py](../../backend/app/routers/settings.py)) | 18 | + `has_activity`, `flag` and a `practised` parameter would make 21. The voice fields move to a new `_voice_status(language, app_settings, installation)` (≈ 9), and `_language_response` drops to ≈ 14 |
| `get_practice_languages_endpoint` (settings.py) | 9 | + 1 dependency → 10 |
| `_FileReader.language` ([loader.py](../../backend/app/language_data/loader.py)) | 12 | + `flag` → 13; `_LANGUAGE_SCHEMA` gains `"flag": str` |
| `_practice_language` ([catalog.py](../../backend/app/practice_languages/catalog.py)) | 9 | + `flag` → 10 |
| `gather_rule_context` ([context.py](../../backend/language_kit/context.py)) | 8 | + `flag_codes` from a new `_shipped_flags(workspace)` → 9 |
| `usePracticeLanguages` ([usePracticeLanguages.ts](../../frontend/src/hooks/usePracticeLanguages.ts)) | 9 | Rewritten on two `useQuery` calls, ≈ 14. `useLoadedLanguages` and `loadLanguages` are deleted |
| `useSettingsForm` ([useSettingsForm.ts](../../frontend/src/components/settings/useSettingsForm.ts)) | 12 | + `useFollowPracticeLanguage(setValues, current)` → 13 |
| `useConversationLanguage` ([useConversationLanguage.ts](../../frontend/src/components/chat/useConversationLanguage.ts)) | 12 | + `targetFlag` → 13 |
| `ConversationLanguageTag`, `EpisodeHeader`, `PracticeLanguageFieldset` | 9, 13, 21 | +1 element each. `PracticeLanguageFieldset` is already 21, so its option mapping moves to a `languageOption(language)` helper → ≈ 17 |
| `App` ([App.tsx](../../frontend/src/App.tsx)) | 18 | Top-level routes nest under `<Route element={<AppLayout />}>`, ≈ 20 |

## Project Structure

### Documentation (this feature)

```text
specs/009-language-switcher-header/
├── spec.md
├── plan.md              # this file
├── research.md          # R1–R9
├── data-model.md        # flag field, practised languages, groups, switch states
├── quickstart.md        # suites, kit check, manual walkthrough, accessibility check
├── contracts/
│   ├── api.md           # GET practice-languages (+flag, +has_activity); PUT settings usage
│   └── ui.md            # header, switcher, flag, Settings, Home, chat/episode headers
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── language_data/
│   │   ├── records.py                  # LanguageRecord.flag
│   │   ├── loader.py                   # strict: flag required (_LANGUAGE_SCHEMA)
│   │   └── languages/{es,de,it}.toml   # flag = …  (written by kit.sh, never by hand)
│   ├── practice_languages/
│   │   ├── __init__.py                 # exports PractisedLanguages
│   │   ├── activity.py                 # NEW: PractisedLanguages protocol
│   │   └── catalog.py                  # PracticeLanguage.flag
│   ├── services/factory.py             # get_practised_languages: conversations ∪ decks
│   └── routers/settings.py             # flag, has_activity; _voice_status extracted
├── language_kit/
│   ├── registry.py                     # Requirement("flag", …)
│   ├── rules.py                        # FlagShipped
│   ├── context.py                      # RuleContext.flag_codes, _shipped_flags
│   └── prerequisites.py                # prereq: frontend flag set installed
└── tests/
    ├── unit/language_data/             # loader refuses missing flag; pinned values gain flag
    ├── unit/language_kit/              # registry table, BROKEN_VALUES, FlagShipped
    ├── unit/practice_languages/        # catalogue carries flag
    └── contract/                       # practice-languages: flag, has_activity

frontend/
├── package.json                        # + flag-icons 7.5.0
├── src/
│   ├── main.tsx                        # import 'flag-icons/css/flag-icons.min.css'
│   ├── App.tsx                         # layout route for the top-level screens
│   ├── components/
│   │   ├── layout/                     # NEW
│   │   │   ├── AppLayout.tsx           # AppHeader + <Outlet/>
│   │   │   └── AppHeader.tsx           # app name, LanguageSwitcher, theme toggle
│   │   ├── language/                   # NEW
│   │   │   ├── LanguageFlag.tsx
│   │   │   ├── LanguageSwitcher.tsx    # button + popup
│   │   │   ├── LanguageListbox.tsx     # groups, options, keyboard
│   │   │   ├── groupLanguages.ts       # pure grouping (FR-009–FR-011)
│   │   │   └── useListboxKeys.ts       # ↑↓ Home End Enter Space Escape
│   │   ├── home/PracticeLanguageNote.tsx   # DELETED (FR-007), with its test
│   │   ├── chat/ConversationLanguageTag.tsx, useConversationLanguage.ts   # + flag
│   │   ├── podcasts/EpisodeHeader.tsx      # + language tag
│   │   └── settings/PracticeLanguageFieldset.tsx, useSettingsForm.ts      # + flag; follows switch
│   ├── hooks/
│   │   ├── usePracticeLanguages.ts     # on TanStack Query, same return shape
│   │   └── useSwitchPracticeLanguage.ts   # NEW: mutation + cache update + invalidation
│   ├── services/api.ts                 # PracticeLanguageOption: flag, has_activity
│   └── pages/Home.tsx, Flashcards.tsx, FlashcardDecks.tsx   # header removed / <header>→<div>
└── e2e/
    ├── language-switcher.spec.ts       # NEW
    ├── fixtures.ts                     # language mocks + flag, has_activity
    ├── home.spec.ts, practice-language.spec.ts   # updated
    └── (others unchanged; must stay green)

docs/design-system.md                   # "Language control" component pattern
docs/architecture.md                    # 009 entry: header layout, PractisedLanguages
```

**Structure Decision**: The existing web-application layout. Two new frontend component folders:
`language/`, the flag and switcher, reusable on any screen, and `layout/`, the shared header. The
backend gains one module (`practice_languages/activity.py`) and no package.

## Phase 0 — Research

Done: [research.md](research.md). Every Technical Context item is resolved:
R1 flags as `flag-icons` SVGs · R2 `flag` as kit-managed language data with a `FlagShipped` rule ·
R3 `has_activity` through a `PractisedLanguages` protocol · R4 save via the existing `PUT` ·
R5 shared query cache and invalidate-all after a switch · R6 a layout route, task screens excluded ·
R7 listbox popup pattern · R8 read-only tag with flag in chat and episode · R9 unknown, missing and
failed states.

## Phase 1 — Design & Contracts

Done: [data-model.md](data-model.md), [contracts/api.md](contracts/api.md),
[contracts/ui.md](contracts/ui.md), [quickstart.md](quickstart.md).

Implementation order that `/speckit-tasks` should keep, each step test first:

1. **Flag data (backend, kit)**. Install `flag-icons` first, so `FlagShipped` has its set. Add the
   `Requirement` and `FlagShipped` rule, then the record field with the loader accepting `flag` as
   optional for now. Run `kit.sh backfill --all`, fill the three packs and `apply` all three.
   Then make `flag` required and `finish` each. The loader cannot require `flag` first: the kit
   imports `app.practice_languages`, which loads every data file strictly when it is imported, so
   a required field that no file has yet stops the kit itself (research R2). Pin `flag` in the
   pinned-values test once `PracticeLanguage` carries it.
2. **API**: `PractisedLanguages` protocol and factory implementation, then the two response fields
   (contract tests first).
3. **Shared state (frontend)**: `usePracticeLanguages` on TanStack Query, then
   `useSwitchPracticeLanguage`. Existing hook tests stay green.
4. **US1 (P1)**: `AppLayout`/`AppHeader` and `LanguageSwitcher` with a flat list. Remove Home's
   header and `PracticeLanguageNote`. Settings follows the switch. E2E: switch from the header.
5. **US2 (P2)**: `groupLanguages` and grouped listbox. E2E: group order and empty-group cases.
6. **US3 (P3)**: `LanguageFlag` in the header, switcher, Settings, chat and episode tags. E2E:
   flags present and not announced.
7. Docs (design system pattern, architecture entry), quickstart walkthrough and accessibility record.

US1 can ship with names only. Flags (US3) depend on step 1. Grouping (US2) depends on step 2.

### Post-Phase-1 re-evaluation: **PASS**

The design added nothing that weakens a row above:
- the contracts change one response by two fields and use an existing `PUT` unchanged, so there is
  no new endpoint, table or provider;
- the settings router's only new import is `PractisedLanguages` from the `practice_languages`
  package root. The flashcards module is reached only by the factory, as it already is;
- `has_activity` is a fact the server can test, and grouping is a pure client function with its
  own unit tests;
- the function-length plan keeps every new or modified backend function ≤ 20 lines; the frontend
  exceptions are listed below.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| `Home` (~270 lines) in `frontend/src/pages/Home.tsx` stays over 20 lines while this feature removes its `<header>` and `<PracticeLanguageNote />` | The change only deletes. `Home` shrinks by ~35 lines and loses `useTheme`, which moves to `AppHeader`. No state, effect or handler is added. | Splitting `Home` into scenario components is the page refactor that 004–007 recorded as a follow-up. Doing it here would mix an unrelated restructuring into a header change. |
| `Flashcards` (~300 lines) and `FlashcardDecks` (~310 lines) stay over 20 lines while their page bar changes from `<header>` to `<div>` | Two tag names per page, so the shared `AppHeader` is the screen's only `banner` landmark (contracts/ui.md). | Same recorded follow-up; the change is two tokens per file. |
| `Chat` (~520 lines) in `frontend/src/pages/Chat.tsx` stays over 20 lines while `ConversationLanguageTag` gains a `flag` prop at its call site | One attribute, `flag={language.targetFlag}`. The value comes from `useConversationLanguage`, which already looks up the catalogue entry. | Same recorded follow-up (`useChatStream`, `useRecorderFlow`). Looking the flag up inside the tag by display name would avoid touching `Chat`, but would key data on a display string. |
