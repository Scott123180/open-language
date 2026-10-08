# Quickstart & Validation: Language Switcher in the Header

**Feature**: 009-language-switcher-header

How to prove the feature works. Contracts: [api.md](contracts/api.md), [ui.md](contracts/ui.md).
Data: [data-model.md](data-model.md).

## Prerequisites

```bash
backend/.venv/bin/pip install -e "backend[dev]"
cd frontend && npm install && npx playwright install chromium   # npm install brings flag-icons
```

## 1. Automated suites (must all pass, zero skips)

```bash
cd backend && .venv/bin/pytest --cov=app --cov=language_kit     # ≥ 90% on new code
.venv/bin/ruff check . && .venv/bin/black --check .
cd ../frontend && npm run lint && npm test -- --run && npm run test:e2e
```

## 2. Language data is complete

```bash
.claude/skills/language-kit/kit.sh requirements    # lists `flag` (needed by 009)
.claude/skills/language-kit/kit.sh check --all     # Spanish, German, Italian: 0 errors
backend/.venv/bin/python -m app.language_data voice-keys   # still loads every file
```

Expected: `es.toml`, `de.toml`, `it.toml` each have `flag = "es" | "de" | "it"`, written by the
kit (each file's header comment still says it is generated).

## 3. Manual walkthrough (real app, `./run.sh`)

Start from a fresh database, or note which languages already have conversations or decks.

| # | Do | Expect | Covers |
|---|---|---|---|
| 1 | Open Home | Header: "Open Language", Spanish flag + "Spanish", theme toggle. No "Practising … · Change in Settings" line | FR-001, FR-007, SC-002 |
| 2 | Open the language control | "My languages": Spanish ✓. "Start a new language": German, Italian, each with a flag | FR-009–FR-011, FR-014 |
| 3 | Press Escape | Closes; focus on the control; still Spanish | FR-005, FR-017 |
| 4 | Open, choose German | Closes within 1 s; header shows German; reload: still German; Settings: German checked | FR-003, SC-001, SC-005 |
| 5 | Start today's scenario | Conversation is in German; chat header shows German flag + "German", no switcher | FR-004, FR-006 |
| 6 | Back Home, open the control | German ✓ first, then Spanish only if it had activity; Italian under "Start a new language" | FR-010, FR-012 |
| 7 | Visit Podcasts, Past Chats, Flashcards, My Decks, Analytics, Settings | Each shows the same header and language | FR-001, SC-002 |
| 8 | On Flashcards, switch to Spanish | The word list reloads for Spanish | Edge: per-language screens |
| 9 | On Settings, change "Correction Feedback" without saving, then switch language from the header | Practice-language radio follows; Correction Feedback keeps the unsaved value | FR-019, edge: unsaved Settings |
| 10 | Stop the backend, choose another language | Switcher stays open with "could not be changed … try again"; header unchanged | FR-008 |
| 11 | Narrow the window below 400px | Control shows the flag only and still works | Edge: narrow screens |
| 12 | Repeat 1–4 in dark mode | Contrast and outlines hold | FR-018 |

## 4. Accessibility check (manual, SC-006)

- Keyboard only: Tab to the control, Enter opens, ↓/↑/Home/End move, Enter chooses, Escape closes,
  focus returns to the control each time.
- Screen reader (Orca on Linux): the control reads "Practice language: Spanish, button, collapsed";
  options read "Spanish, selected" / "German" with their group name; no flag is announced.
- Contrast of the control text, group headings and selected option meet WCAG AA in light and dark.
- Touch targets ≥ 44px.

Record the results in the feature's validation record, as 006–008 did.

## 5. Onboarding still needs no screen change (SC-004)

Dry run with the kit (no need to finish a real language):

```bash
.claude/skills/language-kit/kit.sh scaffold pt --name Portuguese
# Writes specs/009-language-switcher-header/languages/pt/pack.toml. Its guidance for `flag` names
# the flag-icons format and suggests the default voice's region.
.claude/skills/language-kit/kit.sh validate pt
# With `flag = "zz"` the `flag` line FAILs (FlagShipped); with `flag = "pt"` it passes.
rm -r specs/009-language-switcher-header/languages/pt   # the dry run is not committed
```
