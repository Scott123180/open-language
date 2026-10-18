# Quickstart: Validating Recurring Podcast Shows

**Feature**: [spec.md](spec.md) | **Contracts**: [contracts/api.md](contracts/api.md) |
**Data model**: [data-model.md](data-model.md)

This guide shows that the feature works end to end. It does not describe how to build it; that is
in `tasks.md`.

---

## Prerequisites

- The backend venv is set up (`backend/.venv/bin/pip install -e "backend[dev]"`). This feature adds no
  dependencies and no voices (research R13).
- Ollama runs `llama3.1:8b`, needed for §3–§4 only. The automated suites need no model and no
  voice files.
- Playwright Chromium is installed: `cd frontend && npx playwright install chromium`.
- **Back up your database before §4**:
  `cp ~/.open-language/app.db ~/.open-language/app.db.pre-010`. Have at least one 007 episode in it,
  so FR-022 can be checked.

## 1. Automated suites (no model or voice needed)

```bash
backend/.venv/bin/pytest                  # includes the ≥ 90% coverage gate
backend/.venv/bin/ruff check backend && backend/.venv/bin/black --check backend
cd frontend && npm run lint && npm run build && npm test && npm run test:e2e
```

**Expected**: zero failures and zero skips. Beyond the guarantee tables in
[contracts/api.md](contracts/api.md), check that these pass:
- **Upgrade (SC-009, FR-022)**: a database built from a frozen pre-010 schema,
  `tests/fixtures/schema_007.sql`, with seeded podcast episodes:
  - upgrades with every row unchanged, `init_db()` run twice;
  - its episodes appear in Past Chats with `episode_number: null`;
  - every show then opens with `next_episode_number: 1`.
- **One-off isolation (FR-007)**: the golden test pins one-off standing prompts and cues
  byte-for-byte to 007's. A one-off episode's start, lines and sign-off write no series row,
  link row or memory.
- **Consistent hosts (SC-001)**: across 10 scripted series episodes, the per-episode
  `podcast_hosts` rows equal the series hosts every time, except the recast slot after a recast.
- **Bounded memory (FR-006)**: over 200 seeded random catch-up sequences, the caps hold and the
  rendered series section stays ≤ 1,800 characters.
- **Snapshot stability**: resuming a series episode after its series gained new memories rebuilds
  the same standing prompt and cue history byte-for-byte.
- **Theme (FR-021)**: `themed-select.spec.ts` passes in light, dark and system-dark themes, with
  computed contrast ≥ 4.5:1 for normal, selected and focused options.
- **Boundaries**: `test_module_boundaries.py` (extended) and the language-literal guard pass.

## 2. API smoke check (backend running)

Start the app with `./run.sh`, then:

```bash
curl -s localhost:8000/api/podcasts/catalog | python3 -c \
  'import json,sys; d=json.load(sys.stdin); print(len(d["shows"]), [s["title"] for s in d["my_shows"]], d["shows"][7]["series"])'
SHOW=$(curl -s localhost:8000/api/podcasts/catalog | python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin)["shows"][7]))')
curl -s -X PUT localhost:8000/api/podcasts/favourites -H 'Content-Type: application/json' \
  -d "{\"show\": $SHOW, \"is_favourite\": true}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["is_favourite"])'
curl -s -X POST localhost:8000/api/podcasts/shows/discover -H 'Content-Type: application/json' -d '{"avoid_titles": []}' \
  | python3 -c 'import json,sys; print([s["title"] for s in json.load(sys.stdin)["suggestions"]])'
```

**Expected**:
- `8 [] None` on a fresh database: eight ready-made shows, no My shows, and no series for Big
  Little Questions;
- `True`;
- three to five new titles, none of them a ready-made title.

## 3. Hand-run benchmarks (real model)

```bash
backend/.venv/bin/pytest -m benchmark tests/integration/podcasts -k "series or one_off or discovery" -s
```

| Benchmark | Pass bar | Records |
|---|---|---|
| `test_series_recall_benchmark.py` | 20 second episodes. The bars: **≥ 16** with a host line that correctly refers to a specific earlier point, and **0** invented memories (SC-002); **≥ 18** on a topic not already covered (SC-003) | `series-review-sheet.md` rows, filled by hand |
| `test_one_off_isolation_benchmark.py` | 20 one-off episodes of shows with a series in progress: **0** host lines refer to earlier episodes (SC-004) | flagged lines in the review sheet |
| `test_series_latency_benchmark.py` | The median time to episode 10's first `line` frame is within **20%** of episode 1's, on the same series with full memory, 10 runs each (SC-006). Prompt token counts are printed. The catch-up wait straight after a Medium sign-off is p90 **≤ 15 s** (research R6) | printed table |
| `test_discovery_benchmark.py` | 10 requests, each returning **≥ 3** suitable, non-duplicate suggestions or the plain message, within **30 s** (SC-007) | printed table |

If SC-002 or SC-003 fails on `llama3.1:8b`, ship series as **experimental**:
- a note on the setup screen, as 003 and 005 did;
- a record in `docs/architecture.md` § "Open items".

## 4. Manual walkthrough: the spec's stories

Use the default local setup, Spanish, in dark mode. Set the name the hosts use to "Sam".

1. **US1, series continuity**:
   - Open Podcasts and choose **Big Little Questions**. The setup screen offers **Start episode
     1**, with One-off as the other choice. Start it in One host format.
   - Tell Hugo "Odio las mañanas" and something you plan to do this weekend, then **End episode**.
   - Back on Podcasts, the card says "Episode 2 next". Choose it. Expected:
     - **Start episode 2** is the primary action;
     - Hugo has the same name, personality and voice sample;
     - "What the hosts remember" lists the topic and "You hate mornings." within a few seconds;
     - Hugo greets Sam by name, says the show continues, and mentions mornings or the weekend
       plan, on a new question.
2. **US1-4, per language**: switch the practice language to German and open the same show.
   Expected: **Start episode 1**, with German names. Switch back: the Spanish series still offers
   episode 2 or 3, with Hugo.
3. **US1-5, unfinished**: start an episode, leave after two lines, and reopen the show. Expected:
   **Continue episode N** first, and "Start a new episode instead" below it.
4. **Waiting for memory** (research R6):
   - Finish an episode with End episode, go straight back, and press **Start episode N+1** at
     once. Expected: "Hugo and Inés are catching up on episode N. This takes a few seconds.", and
     then the episode starts on its own. Its opening refers to episode N.
   - Repeat with Ollama stopped. Expected: a plain failure message with **Try again** and
     **Start without it**.
5. **US2, one-off**:
   - Choose **One-off episode**, Shuffle a host, and run a few lines. Expected: no mention of
     earlier episodes, and the header says "One-off".
   - Return to the show. Expected: the next episode number and the remembered points are as before.
6. **US3, consistent hosts**:
   - On episode N ≥ 2's setup, check that there is no Shuffle and no personality drop-down.
   - Press **Recast…** on the second host and choose a personality. Expected: the dialog says the
     new host won't know the history. **Cancel** changes nothing.
   - Recast again and **Confirm**. Expected: a new name, and the lead unchanged.
   - Run the episode. Expected: the new host is introduced as new, and Hugo still recalls earlier
     points. In the next episode the new host is kept.
7. **US4, My shows**:
   - Favourite Big Little Questions and Game Day, and generate a show and play one line of it.
   - Restart the app (`./run.sh`). Expected: My shows lists all three with their next episode
     numbers, and the ready-made list is unchanged.
   - Unfavourite Game Day. Expected: it leaves My shows (no series).
   - Unfavourite Big Little Questions. Expected: it stays (series in progress).
8. **US5, Find a new show**:
   - Press **Find a new show**. Expected: 3–5 cards, none already listed. Press **Show me others**.
     Expected: no repeats.
   - Favourite one. Expected: it joins My shows.
   - Start another. Expected: the setup screen opens.
   - Stop Ollama and press Find a new show. Expected: a plain message, and the rest of the screen
     still works.
9. **US6, drop-downs**: in light, dark and system themes, open:
   - the setup personality drop-down;
   - Settings' drop-downs;
   - the chat Level control;
   - the flashcards word filter.

   Expected: each list is drawn on the theme surface with the theme text, and the selected and
   focused options are both clearly marked.
10. **Edge cases**:
   - Set the hosts' name for you to "Hugo". Expected: setup points out the clash, and Start says
     to change your name.
   - Remove one Spanish voice file. Expected: the series host keeps their name, and the missing-voice
     notice of 007 appears.
   - **Start over** a series, then confirm. Expected: Episode 1 next, and the old episodes are
     still in Past Chats.

## 5. Preservation check (SC-009, FR-022)

After §4, compare with the backup:

```bash
sqlite3 ~/.open-language/app.db.pre-010 'select count(*) from conversations; select count(*) from messages; select count(*) from vocabulary_items;'
sqlite3 ~/.open-language/app.db        'select count(*) from conversations where id <= (select max(id) from podcast_episodes);'
```

**Expected**: every pre-010 conversation, message, word and setting is present. Pre-010 podcast
episodes open from Past Chats, and none has a `podcast_series_episodes` row.

## 6. Accessibility check (manual, Principle IV)

- **Keyboard only**:
  - Podcasts: Tab reaches each card's choose button and then its favourite toggle, which announces
    "Favourite Big Little Questions, pressed".
  - Every `ThemedSelect` opens with Enter, Space or Alt+↓; moves with arrow keys and type-ahead;
    closes with Escape (no change); selects with Enter.
- **Dialogs**: Recast and Start over trap focus and return it to the button that opened them, and
  Escape cancels.
- **Screen reader (Orca)**:
  - My shows is announced as a region;
  - a card's description includes "Episode 2 next";
  - suggestions are announced when they arrive;
  - the name-clash hint is read with the name field.
- **Contrast**: check the open lists, the favourite toggle (both states) and the series badges at
  ≥ 4.5:1 in both themes (SC-008). Touch targets are ≥ 44 px.
