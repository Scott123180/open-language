# Quickstart: Validating the Conversation Difficulty Level

**Feature**: [spec.md](spec.md) | **Contracts**: [contracts/api.md](contracts/api.md) |
**Data model**: [data-model.md](data-model.md)

This guide proves the feature works end to end. It does not describe how to build it; that belongs
in `tasks.md`.

---

## Prerequisites

- The backend venv is set up: `backend/.venv/bin/pip install -e "backend[dev]"`. The dev extra now
  includes `wordfreq`, which only the benchmark uses (research R9).
- Ollama is running with the default model (`llama3.1:8b`). This is needed for §3 and §4 only; the
  automated suites need no model.
- Playwright Chromium is installed: `cd frontend && npx playwright install chromium`.

## 1. Automated suites (no model needed)

```bash
backend/.venv/bin/pytest                  # includes the ≥ 90% coverage gate
backend/.venv/bin/ruff check backend && backend/.venv/bin/black --check backend
cd frontend && npm run lint && npm test && npm run test:e2e
```

**Expected**: zero failures and zero skips. The new tests cover every guarantee table in
[contracts/api.md](contracts/api.md), in particular:
- the prompt at Natural is byte-identical to before (FR-004);
- a level change rebuilds the session on the next turn (FR-008, SC-005);
- phrasing caches are level-qualified (research R7).

## 2. Settings API smoke check (backend running)

Start the app with `./run.sh`, then:

```bash
curl -s localhost:8000/api/settings/conversation-levels | python3 -m json.tool
curl -s localhost:8000/api/settings | python3 -c 'import json,sys; print(json.load(sys.stdin)["conversation_level"])'
curl -s -X PUT localhost:8000/api/settings -H 'Content-Type: application/json' \
     -d '{"conversation_level":"elementary"}' | python3 -c 'import json,sys; print(json.load(sys.stdin)["conversation_level"])'
curl -s -o /dev/null -w '%{http_code}\n' -X PUT localhost:8000/api/settings \
     -H 'Content-Type: application/json' -d '{"conversation_level":"expert"}'
```

**Expected**:
- the first command lists four levels, easiest first;
- on a database from before this feature, the second prints `natural`;
- the third prints `elementary`;
- the fourth prints `422`.

## 3. Adherence benchmark (SC-001 – SC-004)

```bash
backend/.venv/bin/pytest -m benchmark -s tests/integration/conversation_levels/test_level_benchmark.py
```

Run it from `backend/`. It plays 4 scenarios × 5 scripted learner turns at each level against the
default local model (research R9). It takes several minutes on a GPU host and longer on CPU.

**Expected output**, recorded against the spec:

| Printed figure | Pass condition |
|---|---|
| `SC-001 Beginner length compliance: n/20` | ≥ 18/20 |
| `SC-002 Elementary / Intermediate length compliance: n/20` | ≥ 17/20 each |
| `SC-003 mean words per sentence` and `share outside top 1,500`, per level | both strictly rise Beginner → Elementary → Intermediate → Natural |
| `SC-004 replies containing native-language words: n` | 0 |

The benchmark also writes `level-review-sheet.md` to the pytest temporary directory (the path is
printed). **Manual step**: mark each Beginner, Elementary and Intermediate reply as within or outside
its level's allowed tenses. SC-001 and SC-002 pass only when the length figures above **and** the
marked tense compliance meet the same thresholds.

If the default local model misses SC-001 or SC-002, the feature ships marked experimental (spec
Assumptions), not with lower thresholds. Record the figures in the PR description.

## 4. Manual walkthrough (user stories)

With the app running (`./run.sh`, open the frontend URL it prints):

1. **US1**: On the Settings screen, choose **Beginner** and save. Start the "Restaurant" scenario.
   The opening line is at most two short sentences in the present tense and ends with one easy
   question. Reply with a complex sentence. The partner answers the substance of your sentence but
   stays simple (FR-013).
2. **US1**: Set the level to **Natural** and start the same scenario. The replies read as they did
   before this feature.
3. **US2**: In a conversation at **Intermediate**, send two messages, then change the header's
   **Level** control to **Beginner**. Check:
   - the control shows "Beginner", and a screen reader announces "Level set to Beginner. It applies
     from the next reply.";
   - no page change and no restart happen;
   - your next message gets a Beginner-level reply that still refers to the earlier turns.
4. **US2 AS4**: Open Settings. It shows Beginner. Change it to Elementary, save, and return to the
   conversation. The header shows Elementary.
5. **US3**: At **Beginner**, request:
   - suggestions: every suggestion is short and in the present tense;
   - alternative phrasings of one of your messages: all at the level;
   - an expression-helper answer: the Spanish phrase is at the level, while the English explanation
     is not limited.
   Then change to Natural and request phrasings for the **same** message again. You get fresh,
   unrestricted phrasings, not the cached Beginner ones.
6. **FR-018**: Grammar explanations, translations and word lookups look the same at every level.
7. **FR-016**: Switch the provider to Claude (if signed in). The level still applies. The first reply
   after a level change may take a few extra seconds while the Claude session is rebuilt (research
   R2).

## 5. Measured criteria

| Criterion | How to measure |
|---|---|
| **SC-006** (≤ 2 interactions, < 5 s) | Time step 3's level change with a stopwatch; with a native `<select>` it is open plus choose |
| **SC-007** (≥ 50% fewer translation requests at Beginner) | Hold one conversation per level on the same scenario (10 turns each), using Translate whenever needed. Then compare per conversation: `sqlite3 ~/.open-language/app.db "SELECT m.conversation_id, COUNT(*) FROM learning_tool_results r JOIN messages m ON m.id = r.message_id WHERE r.tool_type = 'TRANSLATION' GROUP BY 1;"`. The path is `Settings.db_path` in `backend/app/config.py`. |
| **SC-008** (first words within 10% of Natural) | In the browser DevTools Network panel, compare time-to-first-byte of `/message` at Natural and at Beginner, excluding the first turn after a change (research R2) |
| **Accessibility** (Constitution quality gate) | Keyboard-only: Tab to the header Level control, change it with arrow keys, and hear the announcement. Check contrast of the control in light and dark themes. |
