# Implementation Plan: Configurable Podcast Shows

**Branch**: `011-configurable-podcast-shows` | **Date**: 2026-10-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/011-configurable-podcast-shows/spec.md`

---

## Summary

The learner found podcast hosts "too conversational". Three rules caused it:
- the level's reply cap held every host line to two sentences at Beginner;
- One host invited the learner on every line;
- hosts were only ever asked to react.

Episode 45 (Panel, Claude) added four more, revised in on 2026-11-03:
- questions to the learner left behind Continue;
- no subject named;
- a wrap-up that did not wrap up;
- an expert held to two short sentences.

This feature:
- changes those three defaults for every new episode, and fixes the four;
- adds five **Episode settings**: Style, Host lines, How often you're asked, Your role, and Today's
  subject;
- lets a series change any setting **just for this episode** or **from now on**, including
  bringing an expert in through a format switch or a **guest host**.

The design rests on nine decisions from [research.md](research.md):

1. **Old episodes keep old behaviour by construction** (R1, R7):
   - each new episode stores a frozen `podcast_episode_settings` row;
   - an episode without one is pre-feature and runs on `LegacyTalk`, today's prompts, cues and
     invitation rules, byte for byte;
   - new episodes run on `ConfiguredTalk`;
   - `host_talk_for()` is the one place a row becomes behaviour. The 007 and 010 golden tests stay
     green unchanged.
2. **The level owns each sentence; Host lines owns the count** (R2):
   - `conversation_levels` gains a third pure renderer, `with_sentence_rules`. It is the partner
     block without the reply cap, so the roleplay block stays byte-identical;
   - the count (Short 1–2, Medium 3–5, Long 5–8) is stated in the standing prompt and in every cue.
3. **The policy, not the model, decides what each line does** (R3, R4):
   - invitations follow a per-setting hazard table with the 4th-line deadline;
   - discussion lines are `answer` (after a `?`), `follow_up`, or a Style-weighted draw of `react`,
     `explain` or `story`;
   - a line that does not invite is told "Don't ask {label} anything this time": the habit the
     learner noticed.
4. **Long lines start playing as fast as short ones** (R13):
   - podcast lines are streamed from the model sentence by sentence, sanitised per sentence and
     synthesised on one worker;
   - each sentence is sent as a `line_part` frame with its own audio URL, played in order;
   - the complete line is stored and its WAV assembled for Replay;
   - roleplay chat stays batched (the 004 decision).
5. **Series settings are a row; scope is chosen per setting at Start** (R9):
   - the client sends what this episode uses, plus the names to keep `from_now_on`;
   - the server writes the series' new usual values in the episode's transaction, so leaving the
     setup discards everything;
   - no row means the show's standard settings, for every pre-feature series and after a reset.
6. **Guests are cast on request, checked at Start, never kept by the series** (R10–R12):
   - "missed by" marks are derived from who was actually in each episode;
   - a returning host only "heard about" a guest episode;
   - a One host series' stored second host who joins later is introduced as new and knows the
     earlier points only secondhand.
7. **The written line decides who has the turn, within the code's limits** (R19):
   - each cue carries an `Ask` level (`required`, `allowed`, `none`) from the hazards and the deadline;
   - each configured line ends with a hidden `[@Name]` / `[@all]` tag, read by `LineAddress` (with a
     name-and-`?` fallback), stripped before anything is shown, spoken or remembered, and stored as
     the line's `addressee`;
   - `invites_learner` is decided after the line: `required`, or addressed to the learner;
   - the next speaker follows the addressee above balance, and a question to a host gets an `answer`;
   - this reverses 007 R2's "never parse the model's text" for configured episodes only.
8. **One subject per episode, and the hosts end it** (R20, R21):
   - the opening names Today's subject or a concrete one it chooses, or **Suggest subjects** offers
     three not yet covered (one structured call, on demand);
   - the wrap-up says the show is nearly over and asks for a last thought, and the next host line
     signs off, after answering any question.
9. **Explaining lines are longer than reacting ones** (R22):
   - a brief and a full cue phrase inside each Host lines range;
   - configured speaking styles for the expert and the interviewer;
   - step-by-step `explain` and `answer` instructions.

What is new:
- two tables, five additive columns (three on preferences, two on host lines) and optional snapshot
  keys (data-model §2);
- four endpoints: part audio, settings reset, guest casting and subject suggestions;
- additive fields on the catalogue, preferences, episode and series responses;
- new SSE events, `line_started` and `line_part`;
- one renderer in `conversation_levels`, one streaming method on the conversation engine, and one
  thread-to-async bridge.

No new dependency, voice or per-language data.

The real risk is the local model: whether `llama3.1:8b` keeps long Beginner lines simple (SC-002),
answers questions (SC-003), follows the line kinds (SC-004), and writes the address tag (SC-012,
where the fallback carries a missing tag). It is measured with the hand-run
benchmarks and review sheet before any claim. A miss ships configured talk labelled experimental,
as in 003, 005 and 010.

---

## Technical Context

**Language/Version**: Python ≥ 3.11 (`backend/.venv` runs 3.14.4); TypeScript 5.4 / React 18.3

**Primary Dependencies**:
- Backend: FastAPI, SQLAlchemy 2.0, the `ollama` client and the `claude -p` adapter (004). Both
  providers' sessions already yield tokens incrementally (`OllamaSession._stream`,
  `iter_text_deltas`). The standard-library `wave` module joins WAV parts.
- **No new dependencies.** No new voices.
- Frontend: React 18, react-router-dom v6, TanStack Query v5, Vitest + Testing Library,
  Playwright. **No new dependencies**: radio fieldsets and the existing `ConfirmDialog` pattern.

**Storage**: SQLite (WAL, foreign keys on).
- Two new tables via `create_all()`: `podcast_episode_settings` and `podcast_series_settings`.
- Three `podcast_preferences` columns and two nullable `podcast_host_lines` columns (`ask`,
  `addressee`) via `_ADDITIVE_COLUMNS`.
- Optional keys in the series snapshot JSON.
- No existing row is rewritten (data-model §2).

**Testing**:
- pytest unit, contract and integration tests, ≥ 90% coverage;
- seeded property tests (invitation rates and deadline, Style draw, the sentence splitter, and the
  streaming sanitiser against the whole-line sanitiser);
- goldens: 007's one-off and 010's series prompts on `LegacyTalk`, unchanged, plus two new
  configured goldens;
- a frozen `tests/fixtures/schema_010.sql` upgrade test (SC-010, FR-025);
- `benchmark`-marked hand-run checks (quickstart §3);
- Vitest;
- Playwright: three new specs, and `podcast-episode.spec.ts` extended.

**Target Platform**: Linux desktop, local-first (Ollama, Piper, faster-whisper). Claude is opt-in
(004). Everything works offline on the local stack.

**Project Type**: Web application (FastAPI backend + Vite/React frontend).

**Performance Goals**:
- SC-011: after Continue, the first sentence of a Short, Medium or Long line starts playing within
  5 s in 90% of cases on the default setup. That is the time to the first sentence plus one
  sentence's synthesis (R13).
- Start does not call the model unless Today's subject is set (R14). 010 SC-006's measurement
  (no subject) is unaffected.
- Addressing adds no model call and no latency: the tag rides on the last sentence, which is
  already held until flush (R19). Suggest subjects is one structured call, only when pressed (R20).
- Part audio is ready before the previous part ends: one Piper worker, faster than real time.

**Constraints**:
- FR-025: a pre-feature episode's prompt and cues are byte-identical (golden tests on `LegacyTalk`).
- FR-001: the roleplay partner's level block is byte-identical (005 tests unchanged).
- Principle VI:
  - `SubjectCheck` uses the selected structured provider through the factory, and fails with a 503
    and the provider's message;
  - streaming uses the selected session provider, with no fallback;
  - Today's subject reaches a cloud provider only inside the episode context the existing notice
    covers.
- 006/008: no language-code literal outside the catalogues; no per-language data (FR-027).
- 007 R3: saved history is the source of truth. Only complete lines are stored, and a mid-line
  failure ends the session.

**Scale/Scope**:
- one learner, 3 languages, 8 ready-made shows;
- 4 new endpoints, plus additive fields on 5 existing responses and 2 new SSE events;
- about 10 new backend modules (in `app/podcasts/services/` and one in `app/conversation_turns/`),
  and about 23 existing backend files touched (contracts §10);
- frontend: about 13 new podcast components and 5 hooks; `SetupForm`, `SeriesHostCard`, `HostLine`,
  `EpisodeHeader`, `useSetupForm`, `useSetupStart`, `useEpisodeAudio`, `episodeState` and
  `usePodcastEpisode` changed.

*No NEEDS CLARIFICATION items remain. Research R1–R22 settles the design questions; R19–R22 were
added on 2026-11-03 from the episode 45 review (spec Clarifications, Session 2026-11-03).*

---

## Spec interpretations

Points where the spec admits more than one reading. Each is resolved here so the choice can be
reviewed.

1. **FR-003 "Often, every host line" in Panel**: taken literally, Often invites on every host line in
   both formats. FR-026's "Conversation · Short · Often reproduces today's quick back-and-forth" is
   then exact for One host's line length and invitations (the episode 45 fixes still apply). Today's Panel averages about one invitation in 2.3 lines, which is closest to the
   new default, Sometimes (R3).
2. **"The show's standard settings"** (FR-019, FR-025) are One host, Medium length, Balanced, Medium
   lines, Sometimes and the show's own role. They are built in one place, `SeriesSettings.standard`.
   Shows have no standard format of their own today, so the catalogue default stands in. A
   pre-feature Panel series therefore opens its next setup on One host; one This-and-later change
   restores Panel. This follows FR-025 literally.
3. **FR-014, episode 1 of a series** asks no scope question: there are no usual settings yet, so all
   of its choices become the series' usual settings.
4. **FR-016, "changed"** means different from the series' usual value. Setting a field back to its
   usual value clears its scope mark.
5. **Hosts and scope**: a guest is always this episode only, and Recast is always from now on and
   immediate (010 FR-009, FR-023). Neither goes through the scope question, so FR-017's "leaving
   discards" applies to the settings and the guest, while Recast stays 010's confirmed action.
6. **FR-020, "in place of either host"**: at most **one guest per episode**, so a regular host is
   always present and the series' memory always has someone who remembers (R10). This includes the
   automatic expert of a Panel-this-episode switch: inviting a guest on the lead's chair then
   replaces that expert rather than adding a second guest.
7. **FR-024a, from now on**: the series already stores a second host. The switch brings that host
   in, introduced as new to the show, rather than casting another (R12). Recast remains available.
8. **FR-022, "marked as missed"** generalises to any episode a regular host was not in, derived from
   the episode's hosts (R11). This covers one or two guest episodes in a row, and One host episodes
   that a later-joining second host never heard.
9. **FR-005, "asks a question"**: the learner's line contains `?`. A question without one is still
   covered by the standing rule (R4).
10. **FR-002a with a voice missing**: the line streams as text only, as 007 FR-031.
11. **FR-004 in legacy One host episodes**: Jump in is offered wherever the hosts have the floor.
    Legacy One host lines always invite, so the hosts never hold the floor and nothing changes for
    those episodes.
12. **FR-010, "checked by the same suitability rules"**: one structured call at Start, only when a
    subject is given (R14). A 422 decline or a 503 provider error starts nothing.
13. **Today's subject in a series** replaces the series rule "choose a subject not in the covered
    list" with "Today's subject was chosen by {label}: talk about it even if it was covered before".
    That is the spec's edge case.
14. **FR-003, "allowed to invite"**: the hazard draw gives `allowed`, the deadline and Often give
    `required` (R19). The property tests check the share of `allowed`-or-`required` cues. The share
    of lines that actually invite depends on the model and is measured by SC-001.
15. **FR-003a, "asks the learner something"**: the line's addressee is the learner (R19). A question
    the tag and the fallback both miss is a measured miss (SC-012's 95%), not a broken invariant.
16. **FR-003b in One host**: there is no other host, so the addressee is the learner or no one. It
    still decides the invitation.
17. **FR-005, "the learner's question is for both hosts"**: a learner question that names neither
    host, or both, gets the "answer for yourself, then ask {other}" instruction. The first host's tag
    routes it to the second, who answers (R4, R19). No per-language plural words.
18. **FR-007a, "names one subject"**: by instruction only. The subject is not stored apart from the
    opening line and, for a series, the keeper's topic (R20).
19. **FR-007b in Panel after the wrap-up**: Pass on the wrap-up counts as the last thought, so the
    next line signs off (R21).
20. **FR-010a, "from the selected conversation partner"**: the selected structured provider, as
    Find a new show and `SubjectCheck` use (Principle VI).

---

## Constitution Check

*GATE: must pass before Phase 0 research. Re-checked after Phase 1 design; the result is at the
bottom of this section.*

| Principle | Status | How this design satisfies it |
|---|---|---|
| **I. Clean Code**: ≤ 20-line functions, intention-revealing names, no magic values | ✅ | Every probability, count and limit is a named catalogue field (data-model §1). The touched functions and their lengths are listed under *Function-length plan*; none ends over 20. `build_standing_prompt`'s six arguments become one `PromptContext` value. |
| **II. SOLID: SRP** | ✅ | Each piece has one job: <br>• `HostTalk`: how this episode's hosts talk; <br>• `TurnPolicy`: who speaks and which kind of line; <br>• `LineWriter`: turn tokens into kept sentences; <br>• `SpokenParts`: speak sentences and assemble the line; <br>• `SeriesService`: which hosts, settings and snapshot an episode starts with; <br>• `SubjectCheck`: judge a subject; <br>• `LineAddress`: who a written line is for (pure); <br>• `SubjectSuggester`: suggest subjects. <br>Routers only sequence them. |
| **II. SOLID: OCP** | ✅ | New behaviour is a new `HostTalk` implementation. `LegacyTalk` is today's code moved, not edited, and the goldens prove it. A new style, length or frequency is a catalogue entry. |
| **II. SOLID: LSP** | ✅ | `LegacyTalk` and `ConfiguredTalk` honour the same contract (tested through one shared contract test). `stream_live` keeps `stream_turn`'s error contract (`LLMError` with a learner message). |
| **II. SOLID: ISP** | ✅ | `HostTalk` has nine small methods (research R1, amended), each used by the policy, the prompt or the history for every episode. `SeriesStorage` gains two methods. `PodcastStorage` gains none: the settings travel on `NewEpisode`, and `ask` and `addressee` on `NewHostLine`. |
| **II. SOLID: DIP** | ✅ | `EpisodeTurns` depends on `LineWriter` and `SpokenParts`, both injected through `EpisodeDependencies`. `SubjectCheck` and `SubjectSuggester` take a `StructuredLLMProvider`. `SpokenParts` takes the speech lookup and an executor. All are wired in `services/factory.py`. |
| **III. TDD (non-negotiable)** | ✅ | Written first: <br>• the `schema_010.sql` upgrade test and the legacy goldens on `LegacyTalk`, before any prompt change; <br>• `with_sentence_rules`, the catalogues, the policy property tests, the splitter and streaming-sanitiser property tests, and the `SeriesSettings` and snapshot round-trips, before their code; <br>• E2E specs with the SSE fixtures, before the components. |
| **≥ 90% coverage, zero skipped tests** | ✅ | Benchmarks are deselected by marker, not skipped. Streaming is tested with a scripted session provider yielding chosen token splits and errors. `SpokenParts` is tested with a fake TTS and a synchronous executor. |
| **IV. One primary action per screen** | ✅ | Setup: Start (or Continue) only. Episode settings is a disclosure; scope, guests and standard settings are secondary (SC-008). The episode screen is unchanged: Continue, or the learner's reply. |
| **IV. Immediate feedback** | ✅ | The settings summary updates as choices change. Each scope mark appears as the scope is chosen. A guest card shows at once with "Casting…". An arriving line shows its sentences as they play. A declined subject says what to change. |
| **IV. Plain-language, what-to-do-next messages** | ✅ | Every new 404, 422, 503 and 504 and the mid-line error say what to do (data-model §5, contracts §3–§8). |
| **IV. Accessibility** | ✅ | Radio groups with legends; a disclosure with `aria-expanded`; scope and guest dialogs as `alertdialog` with focus trap and return; marks as text; `aria-busy` on the arriving line. Manual check in quickstart §5. |
| **V. Compartmentalization** | ✅ | Podcast code stays inside `app.podcasts`, and its package root does not change. The modules outside it that change do so through their own package roots: <br>• `conversation_levels` (a new pure renderer); <br>• `services/conversation` (a new engine method); <br>• `conversation_turns` (a new bridge). <br>The factory is the only outside importer of `spoken_parts`, `subject_check` and `subject_suggestions` (boundary test extended). |
| **V. Abstractions before implementations** | ✅ | `HostTalk` is declared and contract-tested before either implementation. The `SeriesStorage` additions are tested on fakes before SQLite. |
| **V. No feature-flag / if-debug guards** | ✅ | Legacy versus configured is data: the settings row, mapped once by `host_talk_for`. An "experimental" label, if SC-001–SC-004 miss, is UI copy, as in 005 and 010. |
| **VI. Provider independence** | ✅ | No provider class, registry or catalogue change. Streaming goes through `SessionCapableProvider` sessions both providers already implement. `SubjectCheck` uses the selected structured provider. Failures are surfaced, never redirected. Nothing new leaves the machine on the local stack. |
| **Per-language data** (template gate) | ✅ N/A | No per-language value: no `Requirement` in `backend/language_kit/registry.py`, and no `kit.sh backfill` (research, last section). Address tags use names, `?` and the existing `guest_labels_for` (R19). |
| **Playwright E2E for frontend changes** | ✅ | New: `podcast-episode-settings`, `podcast-series-settings`, `podcast-guests`. Extended: `podcast-episode` (streamed parts, Replay after `line`, mid-line error, One host Jump in). Fixtures in contracts §11. |
| **Linting (ruff, black, ESLint, Prettier)** | ✅ | No tooling change. The ESLint `max-lines-per-function` override already covers the podcast components; new shared files are added to its list if any are created. |

**Initial gate: PASS.** There are no Complexity Tracking items.

### Function-length plan (Boy Scout, quality gate)

Measured on `011-configurable-podcast-shows` @ `bad97c7`, counting the `def` line and docstring.
Every function this feature modifies ends at ≤ 20 lines.

| Function | Today | Change |
|---|---|---|
| `build_standing_prompt` ([prompts.py](../../backend/app/podcasts/prompts.py)) | 18 | Takes a `PromptContext` (show, cast, label, languages, level, series, talk). Sections come from the context and `talk.line_rules` / `talk.extra_sections`; the level block from `talk.speech_rules` → ≈ 14 |
| `render_cue` / `_instruction` (prompts.py) | 12 / 10 | The closing sentence comes from `talk.closing(cue, label)`, and unknown intents go to `talk.instruction` → ≈ 11 / 12 |
| `_show_section` (prompts.py) | 10 | The role comes from the episode; the subject sentence from `_subject_sentence(talk)` → ≈ 12 |
| `_series_section` / `_series_open` (prompts.py) | 16 / 11 | Guest, away and missed-mark lines come from `_guest_lines(series)` and `_point_line(point, series)` → ≈ 18 / 13 |
| `_line_rules` (prompts.py) | 14 | Moves unchanged into `LegacyTalk`; `ConfiguredTalk` has its own, ≈ 18 |
| `_partner_speech_block` ([rules.py](../../backend/app/conversation_levels/rules.py)) | 9 | Becomes `(precedence, cap_line, *_sentence_lines(limits))`, and `_sentence_block` reuses `_sentence_lines`. Output byte-identical → ≈ 8 |
| `TurnPolicy._invites` ([turn_policy.py](../../backend/app/podcasts/services/turn_policy.py)) | 11 | Renamed `_ask`; the hazard and deadline come from `state.talk.ask(run, format, rng)`, returning an `Ask`; the balance rule is kept → ≈ 10 |
| `TurnPolicy._speaker` (turn_policy.py) | 12 | The rule tuple gains `_addressee_of_last_line` between `_addressed_host` and `_balancing_host` (≈ 6 lines, new) → 12 |
| `TurnPolicy._cue` (turn_policy.py) | 10 | `invites_learner=` becomes `ask=`; `is_settle_invite` reads `ask` → 10 |
| `_intent` (turn_policy.py) | 12 | Becomes a method so the Style draw can use the policy's `rng`; `DISCUSS` comes from `state.talk.discussion_intent(state, rng)`, which also holds R21's after-wrap-up table → ≈ 13 |
| `_line_facts` ([episodes.py](../../backend/app/podcasts/services/episodes.py)) | 11 | + `ask` (column, or derived from `invites_learner` via `_stored_ask`) and `addressee` → ≈ 13 |
| `stored_cue` ([cues.py](../../backend/app/podcasts/services/cues.py)) | 10 | `invites_learner=` becomes `ask=line.ask` → 10 |
| `EpisodeTurns._store` ([episode_turns.py](../../backend/app/podcasts/services/episode_turns.py)) | 14 | + `ask`, `addressee`, and `invites_learner=talk.invitation(...)` via `_host_line_for(episode, written)` → ≈ 12 |
| `EpisodeState` / `LoadedEpisode.state` ([episodes.py](../../backend/app/podcasts/services/episodes.py)) | — / 9 | + `talk` field → 10 |
| `LoadedEpisode.standing_prompt` (episodes.py) | 5 | Builds a `PromptContext` → ≈ 6 |
| `turn_actions` (episodes.py) | 7 | `can_pass` reads `has_pass` → 7 |
| `episode_history` / `next_turn_history` ([cues.py](../../backend/app/podcasts/services/cues.py)) | 16 / 10 | Pass `talk` through; the assistant turn's text comes from `talk.replayed_line(...)` via `_host_turns(...)` → ≤ 16 / 10 |
| `EpisodeTurns._line_events` ([episode_turns.py](../../backend/app/podcasts/services/episode_turns.py)) | 12 | Relays `line_started` / `line_part` from `LineWriter.events(...)`, then stores, assembles and sends `line` → ≈ 18 |
| `EpisodeTurns._write_line` | 15 | Moves to `LineWriter`, split into `_attempt` and `_kept_sentences`, each ≤ 20 |
| `EpisodeTurns._speak` | 12 | Replaced by `_assemble_audio(line, stream_id)` → ≈ 8 |
| `_check_message` ([routes.py](../../backend/app/podcasts/routes.py)) | 9 | Unchanged (reads `has_jump_in`) |
| `start_episode` (routes.py) | 18 | Preparation, the subject check and the refusal mapping move to `_prepared_start(...)` → ≈ 15 |
| `_remember_start` (routes.py) | 6 | + last-used settings for one-off starts, via `_last_used(req)` → ≈ 10 |
| `_episode_turns` (routes.py) | 16 | + `writer` and `spoken = Depends(get_spoken_parts)` → 18 |
| `SeriesService.new_episode` ([series.py](../../backend/app/podcasts/services/series.py)) | 18 | `learner_role` comes from `prepared.settings`; + `settings=` → 19 |
| `_series_start` / `_participating` (series.py) | 9 / 4 | + settings resolution (`_series_settings(...)`) and the guest in its slot (`_with_guest`) → ≈ 14 / 8 |
| `_snapshot` (series.py) | 14 | Points via `_remembered_lines(points, present, cast)`; new hosts via `_joining_slots(series, present)` → ≈ 16 |
| `SeriesSnapshot.to_json` / `from_json` ([series_snapshot.py](../../backend/app/podcasts/services/series_snapshot.py)) | 10 / 8 | Optional keys through `_line_json` / `_line_of` → ≈ 13 / 12 |
| `SeriesBrief.of` (series_snapshot.py) | 5 | + guest name and away host → ≈ 10 |
| `SQLitePodcastStorage.create_episode` / `_episode_record` ([sqlite_storage.py](../../backend/app/podcasts/services/sqlite_storage.py)) | 14 / **20** | + settings row and series settings upsert → ≈ 17. `_episode_record` moves its scalar fields into `_record_fields(row)` before gaining `settings=_settings_of(row)` → ≈ 14 |
| `SQLiteSeriesStorage.remembered` / `_series_record` ([sqlite_series_storage.py](../../backend/app/podcasts/services/sqlite_series_storage.py)) | 12 / 15 | + `conversation_id` / + `settings=_settings_record(...)` → 12 / 16 |
| `episode_response` / `_episode_fields` ([responses.py](../../backend/app/podcasts/responses.py)) | 16 / 17 | + `settings`, `is_guest`, `away_host_name` via `_settings_model(record)` and `_guest_fields(episode)` → 16 / 19 |
| `series_detail` (responses.py) | 19 | The host and memory fields move into `_series_members(...)`; + `usual_settings`, `is_standard`, `second_role_personality_id` → ≈ 18 |
| `HostCaster.recast` ([casting.py](../../backend/app/podcasts/services/casting.py)) | 20 | Unchanged. `cast_guest` is new and reuses `_free_names` and a voice helper |
| `ConversationSessionPool.run_turn` ([pool.py](../../backend/app/services/conversation/pool.py)) | 10 | Unchanged. `run_turn_live` is new, with `_first_token_with_one_retry`, each ≤ 20 |
| `SetupForm` ([SetupForm.tsx](../../frontend/src/components/podcasts/SetupForm.tsx)) | ≈ 20 | The format, length and name fields move into `SetupFields`; + `<EpisodeSettings>` → ≈ 17 |
| `SeriesHostCard`, `HostLine`, `EpisodeHeader` | ≤ 20 | + guest actions, the arriving state, the guest and away text, each through a small child component |
| `useSetupForm`, `useSetupStart` | ≤ 20 | Settings state moves to `useEpisodeSettingsForm`, scopes to `useSeriesScopes`; `useSetupStart` sends `settings`, `from_now_on` and `guest` |
| `useEpisodeAudio` / `useNewLineSpeech` ([useEpisodeAudio.ts](../../frontend/src/hooks/podcasts/useEpisodeAudio.ts)) | 17 / 20 | Part playback in a new `usePartQueue`; `useNewLineSpeech` skips lines that were streamed → ≤ 20 |
| `streamHandlers` ([usePodcastEpisode.ts](../../frontend/src/hooks/podcasts/usePodcastEpisode.ts)) | ≈ 8 | + `onLineStarted`, `onLinePart` → ≈ 10 |

### Post-Phase-1 re-evaluation: **PASS**

The design added nothing that weakens a row above:
- the contracts confirm that every API change is additive, old clients ignore the new SSE events,
  and `PodcastStorage` gains no abstract method;
- the data model confirms two additive tables cascading from existing parents, three defaulted
  columns, and snapshot keys that old snapshots load without. No row is rewritten, and pre-feature
  episodes are recognised by the absent row, not a flag;
- outside `app.podcasts`, the changes are one pure renderer, one engine method and one bridge, each
  behind its module's package root; `routers/chat.py`, `routers/audio.py` and every provider are
  untouched;
- the quickstart gives every success criterion and Principle IV claim a concrete check;
- R13 keeps 007 R3's invariant (only complete lines are stored), so streaming adds no state for
  history, memory or Past Chats to reconcile.

---

## Project Structure

### Documentation (this feature)

```text
specs/011-configurable-podcast-shows/
├── spec.md                    # input
├── plan.md                    # this file
├── research.md                # Phase 0: R1–R18
├── data-model.md              # Phase 1
├── quickstart.md              # Phase 1
├── contracts/
│   └── api.md                 # Phase 1
├── checklists/
│   └── requirements.md        # from /speckit-specify
├── talk-review-sheet.md       # created during validation (SC-003, SC-004, SC-009)
└── tasks.md                   # Phase 2 (/speckit-tasks; NOT created here)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── podcasts/
│   │   ├── catalog.py                      # + EpisodeStyle, HostLineLength, InviteFrequency,
│   │   │                                   #   PodcastFormat.has_pass, One host Jump in, constants
│   │   ├── models.py                       # + podcast_episode_settings, podcast_series_settings,
│   │   │                                   #   3 PodcastPreferences columns
│   │   ├── schemas.py                      # + EpisodeSettingsModel, from_now_on, guest, options,
│   │   │                                   #   GuestRequest, response fields
│   │   ├── prompts.py                      # PromptContext; configured sections and cues via HostTalk;
│   │   │                                   #   guest, away, missed marks; subject-check prompt
│   │   ├── responses.py                    # + episode_options, settings, guest, usual_settings
│   │   ├── routes.py                       # start with settings, guest, from_now_on; part audio
│   │   ├── series_routes.py                # + settings reset, guest casting
│   │   ├── discovery_routes.py             # + subject suggestions (R20)
│   │   └── services/
│   │       ├── host_talk.py                # NEW: HostTalk, LegacyTalk, ConfiguredTalk, host_talk_for
│   │       ├── episode_settings.py         # NEW: EpisodeSettings
│   │       ├── series_settings.py          # NEW: SeriesSettings (standard, with_changes)
│   │       ├── subject_check.py            # NEW: SubjectCheck
│   │       ├── subject_suggestions.py      # NEW: SubjectSuggester (R20)
│   │       ├── line_address.py             # NEW: LineAddress, address tags + fallback (R19)
│   │       ├── sentences.py                # NEW: SentenceSplitter
│   │       ├── line_writer.py              # NEW: LineWriter (stream → sentences → sanitise → retry)
│   │       ├── spoken_parts.py             # NEW: SpokenParts, LinePart, WAV assembly
│   │       ├── sanitiser.py                # + StreamingSanitiser (reads the address tag first)
│   │       ├── turn_policy.py              # Ask, addressee rule, discussion intents via state.talk
│   │       ├── episodes.py, cues.py        # talk, settings, guest facts
│   │       ├── episode_turns.py            # relays parts; speech via SpokenParts
│   │       ├── series.py                   # settings, scopes, guests, marks, first appearances
│   │       ├── series_snapshot.py          # RememberedLine, guest_slot, away_host_name
│   │       ├── casting.py                  # + cast_guest
│   │       ├── storage.py, sqlite_storage.py               # settings row, upsert, preferences
│   │       └── series_storage.py, sqlite_series_storage.py # hosts_present, reset_settings, settings
│   ├── conversation_levels/rules.py, __init__.py   # + with_sentence_rules
│   ├── conversation_turns/streaming.py, __init__.py # NEW: iterate_in_thread
│   ├── services/conversation/pool.py, engine.py    # + run_turn_live / stream_live
│   ├── services/factory.py                 # + get_spoken_parts, get_subject_check,
│   │                                       #   get_subject_suggester
│   └── database.py                         # + 5 _ADDITIVE_COLUMNS entries
│   # NOT modified: prompts/templates.py, routers/chat.py, routers/audio.py,
│   #   conversation_summary/*, services/llm/*, services/tts/*, practice_languages/*,
│   #   language_data/*, language_kit/*
└── tests/
    ├── unit/podcasts/                      # catalogues, host talk (contract + goldens), policy
    │                                       #   properties, splitter + streaming sanitiser properties,
    │                                       #   series settings, snapshot forms, guests, subject check
    ├── unit/conversation_levels/           # with_sentence_rules
    ├── unit/services/conversation/         # run_turn_live retry-before-first-token, abandon, error
    ├── unit/test_module_boundaries.py      # + spoken_parts, subject_check
    ├── contract/                           # start fields, part audio, settings reset, guest casting,
    │                                       #   episode and series response fields, SSE events
    ├── integration/podcasts/               # streamed lines, episode settings, series settings,
    │                                       #   guest episodes, upgrade from schema_010,
    │                                       #   *_benchmark.py (hand-run, quickstart §3)
    ├── support/                            # scripted streaming session provider
    └── fixtures/schema_010.sql             # NEW: frozen pre-011 schema with data

frontend/
├── src/
│   ├── services/podcastsApi.ts             # + options, settings, guest, reset, part events
│   ├── hooks/podcasts/                     # NEW: useEpisodeSettingsForm, useSeriesScopes, useGuest,
│   │                                       #   usePartQueue, useSubjectSuggestions; useSetupForm, useSetupStart,
│   │                                       #   useEpisodeAudio, usePodcastEpisode, episodeState changed
│   ├── components/podcasts/                # NEW: EpisodeSettings, StyleFieldset, HostLinesFieldset,
│   │                                       #   AskedFieldset, RoleFieldset, TodaySubjectField,
│   │                                       #   SubjectSuggestions,
│   │                                       #   ScopeDialog, ScopeMark, StandardSettingsButton,
│   │                                       #   GuestDialog, GuestCard, SetupFields, ArrivingLine;
│   │                                       #   SetupForm, SeriesHostCard, HostLine, EpisodeHeader changed
│   └── pages/PodcastSetup.tsx              # passes series usual settings to the form
└── e2e/
    ├── podcast-episode-settings.spec.ts, podcast-series-settings.spec.ts,
    │   podcast-guests.spec.ts              # NEW
    ├── podcast-episode.spec.ts             # + streamed parts, Replay, mid-line error, Jump in
    └── fixtures.ts                         # + episodeOptions, seriesWithSettings, guestDraft,
                                            #   streamedLineFrames
```

**Structure Decision**: keep the web-application layout, and keep everything podcast-shaped
**inside `app/podcasts/`**:
- settings, scopes, guests and line streaming are podcast concepts (shows, hosts, episodes, series,
  cues);
- the three changes outside the module are general mechanisms its owners would accept on their
  own terms:
  - a level renderer without the reply cap;
  - incremental engine streaming;
  - a thread-to-async bridge;
- the frontend's new controls are podcast-only and live in the podcast folders. Colocated
  `*.test.tsx` files follow the existing convention and are left out of the tree.

### Suggested phase order (for `/speckit-tasks`)

1. **Foundation**, which blocks every story:
   - the frozen `schema_010.sql` upgrade test, and the 007 and 010 goldens re-pointed at
     `LegacyTalk`, written first;
   - the catalogues and `PodcastFormat.has_pass`;
   - the two models and the three preference columns;
   - `EpisodeSettings`, then the `HostTalk` ABC with its shared contract test;
   - `LegacyTalk` as a pure move of today's code (goldens green);
   - `NewEpisode.settings`, the settings row in `create_episode`, and `host_talk_for` in
     `LoadedEpisode`;
   - the factory wiring and the extended boundary test.
2. **US1 (P1): hosts talk like podcast hosts**:
   - `with_sentence_rules`;
   - `ConfiguredTalk`: line rules, cue text, the three closings, the covered role, the subject in
     the opening, the wrap-up and sign-off wording, brief/full phrases, configured speaking styles
     (R19–R22);
   - `LineAddress`, the `ask` and `addressee` columns, invitations from the written line, the
     addressee speaker rule, `answer` after a host's question, and the after-wrap-up sign-off
     (property tests);
   - policy invitations and discussion intents (property tests);
   - One host Jump in;
   - **sentence streaming (R13)**: `stream_live`, `iterate_in_thread`, `SentenceSplitter`,
     `StreamingSanitiser`, `LineWriter`, `SpokenParts`, the part route, the SSE events, and the
     frontend part queue and arriving line;
   - `podcast-episode.spec.ts`.

   **Run `test_host_talk_benchmark.py` and the extended latency benchmark here**, before the settings
   build on the defaults.
3. **US2 (P1): episode settings**:
   - `settings` on Start (defaults, validation);
   - `SubjectCheck`;
   - `SubjectSuggester`, `POST /subject-suggestions`, and Suggest subjects on the setup (R20);
   - last-used preferences;
   - `episode_options`;
   - the Episode settings disclosure and fieldsets;
   - Listen hiding;
   - `podcast-episode-settings.spec.ts`.
4. **US3 (P1): series settings and scopes**:
   - `SeriesSettings`, the settings row on series create, `from_now_on`, `usual_settings` and
     `is_standard`, the settings reset;
   - the Panel-this-episode automatic expert (needs the guest casting of phase 5's backend; build
     `cast_guest` and the guest endpoint here);
   - from-now-on Panel bringing the second host in as new;
   - `ScopeDialog`, `ScopeMark`, `useSeriesScopes`, `StandardSettingsButton`;
   - `podcast-series-settings.spec.ts`, including SC-007.
5. **US4 (P2): guest hosts**:
   - guest validation at Start, at most one guest;
   - snapshot `guest_slot` and `away_host_name`, guest and away prompt lines and cues;
   - `hosts_present` and missed marks;
   - `GuestDialog`, `GuestCard`, the episode header's guest and away text;
   - `podcast-guests.spec.ts`;
   - `test_guest_episode_benchmark.py`.
6. **Polish**:
   - `talk-review-sheet.md`;
   - the experimental note if SC-001–SC-004 miss;
   - R18's context measurement recorded;
   - `docs/architecture.md`: host talk, sentence streaming (amend the "batched tokens" note for
     podcasts), series settings, guests;
   - the CLAUDE.md domain-module note and Recent Changes;
   - the quickstart §5 manual accessibility check.

---

## Complexity Tracking

> No Constitution Check violations: nothing to justify.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | n/a | n/a |
