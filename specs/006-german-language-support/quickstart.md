# Quickstart: Validating German Language Support

**Feature**: [spec.md](spec.md) | **Contracts**: [contracts/api.md](contracts/api.md) |
**Data model**: [data-model.md](data-model.md)

This guide proves that the feature works end to end. It does not describe how to build it; that
belongs in `tasks.md`.

---

## Prerequisites

- The backend venv is set up: `backend/.venv/bin/pip install -e "backend[dev]"`. There are no new
  dependencies; `wordfreq` is already in the dev extra.
- The German voices are downloaded: `./run.sh --setup`. This fetches `de_DE-thorsten-medium` and
  `de_DE-kerstin-low` into `~/.local/share/piper-voices`, about 126 MB, once.
- Ollama is running with `llama3.1:8b`. It is needed for §3–§5 only; the automated suites need no
  model and no voice files.
- Playwright Chromium is installed: `cd frontend && npx playwright install chromium`.
- **Back up your database before §4**: `cp ~/.open-language/app.db ~/.open-language/app.db.pre-006`.

## 1. Automated suites (no model or voice needed)

```bash
backend/.venv/bin/pytest                  # includes the ≥ 90% coverage gate
backend/.venv/bin/ruff check backend && backend/.venv/bin/black --check backend
cd frontend && npm run lint && npm run build && npm test && npm run test:e2e
```

**Expected**: zero failures and zero skips. The new tests cover every guarantee table in
[contracts/api.md](contracts/api.md), in particular:
- the catalogue invariants I1–I6, including "every voice is in `run.sh`" ([data-model](data-model.md) §1);
- the pre-006 database fixture upgrades with every row unchanged, `init_db()` run twice (SC-005);
- mixed Spanish/German fixtures never leak across `language=` (SC-006);
- no prompt contains a bare language code (research R2);
- no text is synthesised with another language's voice (FR-018).

## 2. API smoke check (backend running)

Start the app with `./run.sh`, then:

```bash
curl -s localhost:8000/api/settings/practice-languages | python3 -m json.tool
curl -s localhost:8000/api/settings/voices | python3 -c \
  'import json,sys; [print(v["key"], v["language"], v["is_installed"]) for v in json.load(sys.stdin)]'
curl -s -X PUT localhost:8000/api/settings -H 'Content-Type: application/json' \
  -d '{"target_language":"de"}' | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["target_language"], d["tts_voice"])'
curl -s -o /dev/null -w '%{http_code}\n' -X PUT localhost:8000/api/settings \
  -H 'Content-Type: application/json' -d '{"tts_voice":"es_ES-davefx-medium"}'
curl -s localhost:8000/api/flashcards/decks?language=de | python3 -m json.tool
curl -s -o /dev/null -w '%{http_code}\n' localhost:8000/api/flashcards/decks
```

**Expected**:
- two languages, both `is_voice_installed: true`;
- four voices, with the two `de` voices installed;
- `de de_DE-thorsten-medium`;
- `422` (a Spanish voice while German is selected);
- `[]` (no German decks yet);
- `422` (the `language` parameter is required).

Switch back before continuing:

```bash
curl -s -X PUT localhost:8000/api/settings -H 'Content-Type: application/json' -d '{"target_language":"es"}'
```

## 3. Hand-run benchmarks (real model, real voice)

```bash
backend/.venv/bin/pytest -m benchmark tests/integration/practice_languages -s
```

| Benchmark | Pass bar | Records |
|---|---|---|
| `test_german_benchmark.py` | ≥ 95% of 50 partner replies (10 scenarios × 5 turns) have no flagged non-German word after human review of the flagged ones (SC-002) | `specs/006-german-language-support/german-review-sheet.md` |
| `test_transcription_benchmark.py` | ≥ 18 of 20 sentences have every umlaut or ß word exact and a word error rate ≤ 20% (SC-003) | Printed table: sentence, transcript, WER, pass |

If SC-002 fails on `llama3.1:8b`, record it in `docs/architecture.md` § "Open items", as 003 and
005 did (spec Assumptions: "Quality limits carry over"). If SC-003 fails on `base`, re-run with
`OPEN_LANGUAGE_WHISPER_MODEL=small`. If that passes, document `small` as the recommended German
setting.

## 4. Manual walkthrough: the spec's stories

Keep a stopwatch for step 1.

1. **US1, SC-001**: From Home, note the "Practising **Spanish**" line. Open Settings, choose
   **German**, and Save. Go back to Home: it now says "Practising **German**". Start *Order at a
   Restaurant*.
   **Expected**:
   - under 30 s from Home to the first German greeting;
   - the reply is spoken in the Thorsten voice;
   - the chat header shows "German", with no control.
2. **US1-2**: Record "Ich hätte gern einen Kaffee und ein Stück Kuchen, bitte." Expected: the
   transcript shows `hätte` and `Stück` with umlauts.
3. **US1-4, SC-004**: Use each tool once on a German reply: translation, alternative phrasing, word
   lookup (select `Stück`), suggestions, and the expression helper.
   **Expected**:
   - the German-side text is in German, and every explanation is in English;
   - the helper panel label reads **English → German**.
4. **US1-5**: Turn on Gentle corrections and write "Ich habe gestern nach Berlin gefahren."
   **Expected**: a correction to `bin … gefahren`, explained in English. "Grüß Gott" and "Servus"
   are **not** flagged (regional German).
5. **US1-6**: Set the level to Beginner in the chat header. Expected: short, simple German replies.
   The experimental warnings are still shown on Settings.
6. **US1-7**: Write "Where is the bathroom?" in English. Expected: the partner asks you, in German,
   to use German.
7. **US3**: Save `Stück` and two more words. Open Flashcards.
   **Expected**:
   - only the three German words are listed;
   - generating and practising a deck plays each word in the German voice;
   - Analytics counts only German practice.
8. **US2, SC-005**: Switch to Spanish in Settings.
   **Expected**:
   - the voice list shows only Spanish voices, with your pre-upgrade choice selected;
   - Flashcards shows only your Spanish words, decks and statistics;
   - Past Chats lists both conversations, labelled **Spanish** and **German**.

   Open an old Spanish conversation and continue it by voice: the replies are in Spanish, spoken
   in the Spanish voice, and the transcription is Spanish. Now switch the setting to German
   **without leaving the page**, and send another message: it stays Spanish (US2-3).
9. **Edge case, in-progress session**: Start a Spanish flashcard session. In a second tab, switch to
   German, then finish the session in the first tab. Expected: the summary and the Spanish
   analytics include it, and German analytics do not.
10. **FR-023**: Save `Hotel` from a German conversation and from a Spanish one. Expected: two
    separate words, each in its own language's list, with separate progress.

**SC-005 check**: run this **after step 8 and before step 9**. Step 9 practises Spanish flashcards,
which updates word classifications by design. Compare the pre-existing rows against the backup:

```bash
OLD=~/.open-language/app.db.pre-006 NEW=~/.open-language/app.db
for t in conversations messages vocabulary_items decks practice_sessions card_results; do
  cols=$(sqlite3 "$OLD" "select group_concat(name) from pragma_table_info('$t')")
  last=$(sqlite3 "$OLD" "select coalesce(max(id), 0) from $t")
  q="select $cols from $t where id <= $last order by id"
  diff <(sqlite3 "$OLD" "$q") <(sqlite3 "$NEW" "$q") >/dev/null \
    && echo "$t unchanged" || echo "$t CHANGED"
done
```

**Expected**:
- every table reports "unchanged", because only the pre-006 columns of pre-006 rows are compared;
- `sqlite3 "$NEW" "select distinct target_language from decks"` prints only `es` for the old decks.


## 5. Offline, voice-missing and accessibility checks

- **SC-007 (offline)**: Select Ollama and German, then disconnect the network (`nmcli networking
  off`, or unplug). Hold a three-turn German conversation by voice. Expected: every turn is
  transcribed, answered and spoken. Reconnect afterwards.
- **SC-003 (your own voice)**: Read the 20 benchmark sentences (printed by §3) aloud into the chat.
  Expected: at least 18 have their umlauts and ß correct and their meaning intact.
- **FR-018 (voice missing)**:
  1. Rename `de_DE-thorsten-medium.onnx` to `….bak` and reload a German conversation.
     **Expected**:
     - one plain notice says the German voice isn't installed and to run `./run.sh --setup`;
     - there is no audio and no Spanish voice;
     - text chat still works;
     - Settings shows the same hint under Voice;
     - a German flashcard's play button shows the same message.
  2. Restore the file.
- **Accessibility (Constitution IV, manual)**, on Settings, Home, Chat and Past Chats:
  - the Practice-language radios are keyboard-operable and announced with their group label;
  - the voice-unavailable notice is announced (`role="status"`);
  - the language tag and badges pass contrast in light and dark mode (design-system tokens only);
  - touch targets are ≥ 44 px.

## 6. Restore (optional)

```bash
cp ~/.open-language/app.db.pre-006 ~/.open-language/app.db   # only if you want to discard the walkthrough
```
