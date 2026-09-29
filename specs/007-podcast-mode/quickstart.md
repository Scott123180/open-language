# Quickstart: Validating Podcast Mode

**Feature**: [spec.md](spec.md) | **Contracts**: [contracts/api.md](contracts/api.md) |
**Data model**: [data-model.md](data-model.md)

This guide shows that the feature works end to end. It does not describe how to build it; that is
in `tasks.md`.

---

## Prerequisites

- The backend venv is set up with `backend/.venv/bin/pip install -e "backend[dev]"`. The feature
  adds no dependencies.
- Voices: `./run.sh --setup` has already fetched two voices per language (006). No new download is
  needed (research R7).
- Ollama is running with `llama3.1:8b`. You need it for §3–§5 only. The automated suites need no
  model and no voice files.
- Playwright Chromium is installed: `cd frontend && npx playwright install chromium`.
- **Back up your database before §4**:
  `cp ~/.open-language/app.db ~/.open-language/app.db.pre-007`.

## 1. Automated suites (no model or voice needed)

```bash
backend/.venv/bin/pytest                  # includes the ≥ 90% coverage gate
backend/.venv/bin/ruff check backend && backend/.venv/bin/black --check backend
cd frontend && npm run lint && npm run build && npm test && npm run test:e2e
```

**Expected**: zero failures and zero skips. The new tests cover every guarantee table in
[contracts/api.md](contracts/api.md), in particular:
- the catalogue invariants P1–P7 ([data-model](data-model.md) §1.6);
- the turn-policy properties over ≥ 1,000 seeded episodes per format: invitation deadline, run
  cap, 25% share, addressed host first, wrap-up timing and the Listen sign-off (data-model §5,
  the automated half of SC-002);
- the sanitiser never lets another participant's label through (FR-012);
- cue histories re-render byte-for-byte, and a trimmed line forces a rebuild (research R3);
- the pre-007 database fixture upgrades with every row unchanged, with `init_db()` run twice
  (SC-011);
- the chat router's tests pass **unmodified** after the move to `conversation_turns` (research
  R11);
- no language code literal appears outside the catalogues (the existing guard, now also covering
  `app/podcasts` and `app/conversation_summary`).

## 2. API smoke check (backend running)

Start the app with `./run.sh`, then:

```bash
curl -s localhost:8000/api/podcasts/catalog | python3 -c \
  'import json,sys; d=json.load(sys.stdin); print(d["language_name"], len(d["shows"]), len(d["personalities"]), d["voices"])'
curl -s localhost:8000/api/podcasts/preferences | python3 -m json.tool
curl -s -o /dev/null -w '%{http_code}\n' -X POST localhost:8000/api/podcasts/shows/generate \
  -H 'Content-Type: application/json' -d '{"idea":"   "}'
curl -s -X POST localhost:8000/api/podcasts/shows/surprise -H 'Content-Type: application/json' -d '{}' \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["title"], [h["name"] for h in d["hosts"]])'
curl -s -o /dev/null -w '%{http_code}\n' localhost:8000/api/conversations/1/summary
```

**Expected**:
- `Spanish 8 10 {'installed_count': 2, 'shared_voice_notice': None, 'unavailable_message': None}`;
- the default preferences (`one_host`, Show text off, no interests);
- `422` for the empty idea;
- a title and two different Spanish names;
- `200` (or `404` on an empty database).

## 3. Hand-run benchmarks (real model, real voices)

```bash
backend/.venv/bin/pytest -m benchmark tests/integration/podcasts -s
backend/.venv/bin/pytest -m benchmark tests/integration/conversation_summary -s
```

| Benchmark | Pass bar | Records |
|---|---|---|
| `test_panel_turn_taking_benchmark.py` | 10 Panel episodes × 10 learner turns: every `invites_learner` line addresses the learner (question or direct invitation, human-checked when flagged), and each host has ≥ 25% of lines (SC-002) | printed table |
| `test_single_speaker_benchmark.py` | 10 Listen and 10 Panel episodes: 0 stored lines contain another participant's speech; the `was_trimmed` rate is recorded (SC-003) | printed table |
| `test_host_language_benchmark.py` | ≥ 95% of host lines have no flagged foreign word, in both languages (SC-005; the 006 `wordfreq` check) | printed table |
| `test_host_level_benchmark.py` | Host lines meet level limits at least as often as roleplay replies, at each level below Natural (SC-006; the 005 measure) | printed table |
| `test_generator_benchmark.py` | ≥ 18 of 20 ideas give an on-topic, playable show; 20 Surprise me presses give ≥ 15 distinct topics (SC-007, SC-008) | printed table |
| `test_podcast_latency_benchmark.py` | p90 time from `/next` to the `line` frame ≤ 5 s over 50 presses; also records `prompt_eval_count` on a Long episode (SC-009, research R14) | printed table |
| `test_summary_benchmark.py` | p90 ≤ 10 s from request to `ready` over 20 summaries (SC-014) | printed table + `summary-review-sheet.md` rows |

**Review sheets**, filled by hand:
- `specs/007-podcast-mode/speaker-review-sheet.md` (SC-004): 10 episodes with labels stripped;
  ≥ 80% of lines correctly attributed.
- `specs/007-podcast-mode/summary-review-sheet.md` (SC-012, SC-013): 20 summaries, 10 roleplay and
  10 podcast, in both languages. The bar is 0 invented statements, ≥ 90% main-point coverage, 100%
  same points across the two versions, and level limits met at least as often as roleplay replies.

If a quality bar fails on `llama3.1:8b`, record it in `docs/architecture.md` § "Open items", as 003,
005 and 006 did (spec Assumptions: "Quality limits carry over").

**Claude (FR-033)**: if you use Claude, also run the live podcast check (deselected by default).

```bash
backend/.venv/bin/pytest -m claude_live tests/live -k podcast
```

**Expected**: a Panel opening, one Continue and one learner reply succeed. The second `/next` reuses
the live session (one `claude` process for the episode).

## 4. Manual walkthrough: the spec's stories

Keep a stopwatch for step 1.

1. **US1 and SC-001 (One host)**:
   - From Home, open **Podcasts**. Check that there are ≥ 6 show cards, each with a title, a topic
     line, host(s) and your role.
   - Pick *Weekend Food Talk*. On setup, the format is **One host** (first time) and the length is
     **Medium**. Press **Start episode**.

   **Expected**:
   - under 30 s from Home to the host's first line;
   - the opening introduces the show, the host and you, and ends with a question, all in Spanish;
   - it is spoken in the host's voice.
2. **US1-3 to US1-5**: Reply five times, typed and spoken. Use translation, word lookup, save word,
   suggestions and the expression helper once each, with corrections set to Gentle.
   **Expected**:
   - the host stays in persona and on topic, and each line invites you;
   - every tool behaves as in roleplay;
   - the saved word appears under Spanish in Flashcards.
3. **US6 (Summary)**:
   - Open **Summary**. Check that there are ≤ 5 short Spanish points and nothing that was not said.
   - Switch to **English**, then back.
   - Close it, then reply twice more and open it again.

   **Expected**:
   - English shows the same points;
   - closing the panel changed nothing;
   - the reopened summary covers the new lines.
4. **US1-6, US1-7**: Leave the episode, open **Past Chats**, and check that the row reads "Podcast ·
   One host · Lucía". Open it and reply once. Then choose **End episode**.
   **Expected**: the same host and voice as before, then a sign-off, and the episode marked
   finished.
5. **US2 (Listen)**:
   - Pick *Tech for Normal People*, choose **Listen**, and start it.
   - Press **Continue** through to the sign-off. Along the way, tap a hidden line, replay it, and
     translate it.
   - Turn on **Show text**, then start another Listen episode.

   **Expected**:
   - speaker names with hidden words, and two clearly different voices;
   - nothing plays until Continue;
   - no host speaks more than three lines in a row;
   - a sign-off at about 20 host lines;
   - the new episode starts with Show text on.
6. **US3 (Panel), SC-002 by hand**: Start a Panel episode and take ten turns. On one turn, address
   the second host by name. Press **Pass** once, and **Jump in** once while the hosts are talking.
   **Expected**:
   - you are invited within four host lines every time, and the banner says "Your turn";
   - the named host answers first;
   - after Pass, the hosts carry on and invite you again;
   - Jump in lets you speak at once.
7. **US4 (Generator)**:
   - Enter "living abroad as a nurse" and generate. Press **Another version**.
   - Enter "   " and generate, then enter an unsuitable idea.
   - Add the interests "football, cooking" and press **Surprise me** five times.

   **Expected**:
   - a complete show that opens on setup, then a different version;
   - a plain message offering Surprise me, for both the blank and the unsuitable idea;
   - most suggestions lean to football or cooking, and none repeats.
8. **US5 (Hosts)**: On a Panel setup, shuffle each host three times and change one personality.
   Play each host's ▶ sample.
   **Expected**:
   - the hosts never share a name, voice or personality;
   - the samples use the two voices;
   - the episode's hosts match the final choices.
9. **Level and language, mid-episode**:
   - In a Panel episode, switch the chat-header level to **Beginner** and press Continue.
   - In Settings, switch the practice language to German, return to the episode and press Continue.

   **Expected**:
   - at Beginner, the next line is short and simple;
   - the episode stays in Spanish with the same hosts;
   - a new episode starts in German with German names and voices.
10. **Voice edge cases**:
    - Temporarily move `es_ES-davefx-medium.onnx` out of `~/.local/share/piper-voices`. Open the
      Panel setup, then resume the Panel episode.
    - Restore the file afterwards.

    **Expected**:
    - on setup, the shared-voice notice shows before starting;
    - on resume, the plain message for that host's voice appears, their lines stay in text, and
      the other host still speaks;
    - no line is ever read in a different voice.
11. **Provider failure**: Stop Ollama and press Continue. Then start Ollama and press Retry.
    **Expected**:
    - a plain message with what to do, and nothing added to the transcript;
    - the retry produces the line;
    - the provider was never switched.

## 5. Offline and preservation checks

- **SC-010**: Disconnect the network, keep the local defaults, and run a Panel episode with spoken
  input for five turns. **Expected**: everything works: transcription, both host voices, and every
  line.
- **SC-011**: After §4, compare the backup's conversations, messages, vocabulary, decks and
  settings against the live database:

  ```bash
  for t in conversations messages vocabulary_items decks; do
    sqlite3 "$HOME/.open-language/app.db" "ATTACH '$HOME/.open-language/app.db.pre-007' AS old;
      SELECT '$t', count(*) FROM (SELECT * FROM old.$t EXCEPT SELECT * FROM main.$t);"
  done
  ```

  **Expected**: `0` for every table, so no pre-existing row changed or disappeared. For
  `app_settings`, compare the columns by hand: they are unchanged apart from the new
  `summary_language` column, which reads `conversation`.
  Open an old roleplay conversation: it behaves as before, and the header now has a Summary button.

## 6. Accessibility check (manual, Principle IV)

On Podcasts, setup and episode screens, in light and dark mode:
- keyboard only: every control is reachable in order, and Continue has the focus after a line
  arrives;
- a screen reader announces the turn banner changes and names hidden lines ("Show Lucía's line");
- contrast: host name labels and hidden-line placeholders meet 4.5:1, using design-system tokens
  and no hard-coded colours;
- touch targets are ≥ 44 px at a 360 px width.
