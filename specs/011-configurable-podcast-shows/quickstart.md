# Quickstart: validating Configurable Podcast Shows

**Feature**: `011-configurable-podcast-shows` | **Contracts**: [contracts/api.md](contracts/api.md)

How to prove the feature works, from automated suites to the hand-run model checks. Run every command
from the repository root.

---

## 1. Prerequisites

- `backend/.venv` with dev dependencies: `backend/.venv/bin/pip install -e "backend[dev]"`
- Frontend dependencies and Chromium: `cd frontend && npm ci && npx playwright install chromium`
- For §3 only:
  - Ollama with `llama3.1:8b`;
  - the Piper voices `run.sh` downloads;
  - optionally a signed-in Claude Code, for FR-027.

## 2. Automated checks (no model, no voices)

```bash
cd backend
.venv/bin/pytest                                   # unit, contract, integration; ≥ 90% coverage
.venv/bin/ruff check . && .venv/bin/black --check .
cd ../frontend
npm run lint && npm test -- --run && npm run test:e2e
```

Expected: zero failures and zero skips. The `benchmark` marker is deselected by default. The
feature-specific evidence is:

| Proves | Test |
|---|---|
| FR-025, SC-010 | `tests/integration/podcasts/test_configured_upgrade_preserves_data.py` loads a frozen `tests/fixtures/schema_010.sql` with an unfinished One host episode and a series. It checks that the episode resumes with the legacy prompt (byte-equal to the 007 golden) and that the series opens on standard settings with its hosts, count and memory |
| FR-001, FR-002 | Unit tests of `with_sentence_rules` (no reply cap, Natural unchanged) and of the configured prompt and cue goldens |
| FR-003, SC-005 | Seeded property tests of `TurnPolicy` with each `InviteFrequency`: rate bands, and never more than 4 host lines in a row without an invitation |
| FR-005, FR-006 | Policy tests: `answer` after a `?`, `follow_up` after two, Style weights over 10,000 draws |
| FR-002a | `SentenceSplitter` and `StreamingSanitiser` property tests (streamed result equals the whole-line sanitiser). `test_streamed_lines.py` checks part frames before `line`, part audio served, the joined WAV for Replay, and an error mid-line leaving nothing stored |
| FR-012, FR-013 | `test_episode_settings.py`: settings survive a resume after the preferences change; one-off starts update last-used, series starts do not |
| FR-014–FR-019, SC-006 | `test_series_settings.py`: episode 1 sets the usual settings; Just this episode leaves the next setup's `usual_settings` unchanged; from now on shows on the next two; reset; count and memory untouched |
| FR-020–FR-024a | `test_guest_episodes.py`: guest validation, at most one guest, Panel-this-episode auto-expert, from-now-on Panel brings the stored second host in as new, missed marks in the next snapshot |
| SC-007, SC-008 | `podcast-series-settings.spec.ts` (expert in 3 choices) and `podcast-episode-settings.spec.ts` (defaults need no opening) |

## 3. Hand-run model checks (`benchmark` marker)

```bash
cd backend
.venv/bin/pytest -m benchmark -s tests/integration/podcasts -k "host_talk or guest_episode or latency"
```

| Benchmark | Prints | Target |
|---|---|---|
| `test_host_talk_benchmark.py` | Per episode: median sentences per discussion line, the invitation share, the share of sentences within 8 words, the share of present-tense sentences, the intent counts; the learner-question transcripts for review | SC-001: median ≥ 3 sentences and ≤ 50% inviting. SC-002: ≥ 90% within length and ≥ 90% present tense. SC-004: Presented ≥ 40% and Conversation ≤ 20% explain or story |
| `test_guest_episode_benchmark.py` | 10 guest episodes, then each following episode's returning-host lines | SC-009, reviewed in the sheet |
| `test_podcast_latency_benchmark.py` (extended) | p90 to the first part's audio, for Short, Medium and Long lines; `prompt_eval_count` at the end of a Long · Long-lines episode | SC-011: p90 ≤ 5 s each. R18: record whether the context truncates |

Fill [talk-review-sheet.md](talk-review-sheet.md), created during validation:
- SC-003: was each of at least 20 learner questions answered in the very next host line?
- SC-009: guest introduced as a guest; no "I was there" from the returning host.
- A spot-check of the counted intents (SC-004).

If SC-001 to SC-004 miss on `llama3.1:8b`, record the figures in `docs/architecture.md` § "Open
items" and ship configured talk with the experimental note (spec Assumptions).

## 4. Manual walk-through (the learner's scenario)

1. Settings: Spanish, Beginner. Podcasts → Big Little Questions → One host, Medium, Start (Episode
   settings untouched).
   - Hugo's opening is several short sentences.
   - Not every line ends with a question.
2. Type "¿Por qué la tostada cae del lado de la mantequilla?".
   - The next line answers: the table's height, the half turn.
   - It is not a question back.
3. Press Continue on a Long-lines episode. The first sentence is heard within about 5 s, and the rest
   follows without a gap. Replay plays the whole line.
4. While the host has the floor in One host, **Jump in** is offered.
5. Next episode's setup:
   - choose Panel, then **Just this episode**;
   - an expert guest appears, cast for today, and the format is marked "this episode";
   - Start. The guest is introduced as joining today.
6. Next setup: back to One host with the usual settings. Change Style to Presented, then **This and
   later episodes**. Check that the two following setups start on Presented.
7. With Panel as the usual format, use **Invite a guest…** on the second host and choose Expert.
   - The episode says Clara is away.
   - In the next episode, Clara may say she heard about it, never that she was there.
8. **Use the show's standard settings**, then confirm. The setup returns to One host · Balanced ·
   Medium lines · Asked sometimes, and the episode count is unchanged.

## 5. Accessibility check (Principle IV, manual)

In both themes, at 360 px and at desktop width:
- the Episode settings toggle announces expanded or collapsed and the summary;
- every radio group has a legend;
- the scope dialog traps focus and returns it to the changed control, and Escape reverts;
- scope marks are readable text with contrast ≥ 4.5:1;
- guest badges are text, not colour alone;
- the arriving line is announced once complete, not sentence by sentence (`aria-busy`);
- touch targets are ≥ 44 px.
