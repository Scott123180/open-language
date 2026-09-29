# Implementation Plan: Podcast Mode

**Branch**: `007-podcast-mode` | **Date**: 2026-09-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/007-podcast-mode/spec.md`

---

## Summary

Add **Podcasts**, a second practice activity next to roleplay. The learner picks a ready-made show,
generates one from an idea, or presses Surprise me, and runs it in one of three formats:
- **One host**: the learner and one host;
- **Panel**: the learner and two hosts;
- **Listen**: two hosts, with the learner listening and pressing Continue.

Hosts have names, personalities and voices, speak at the learner's level, and every existing
learning tool works on their lines. A **Summary** of the conversation so far, in the conversation's
language or English, is added to podcast episodes and roleplay conversations alike.

The design rests on four decisions from [research.md](research.md):

1. **An episode is a conversation** (R1). Starting one creates an ordinary `conversations` row, and
   every line is an ordinary `messages` row. So translation, lookup, saved words, corrections,
   transcription, speech caching, Past Chats and the language rules of 006 all work unchanged.
   Three podcast tables record only what is podcast-specific: the episode, its hosts, and who
   spoke each host line and why.
2. **The code runs the turn-taking; the model writes one line** (R2). A pure `TurnPolicy` enforces
   FR-013–FR-019 exactly:
   - who speaks;
   - the three-in-a-row cap and the 25% share;
   - the invitation by the fourth line;
   - the addressed host first;
   - the wrap-up at the chosen length.

   The model is only ever asked for "Marco's next line", and a sanitiser cuts anything spoken by
   someone else (R4).
3. **Host lines use the existing conversation engine** (R3). They go through
   `ConversationEngine` under a new `SessionKind.PODCAST`. Short producer cues act as the user
   turns between host lines; they are re-rendered from stored facts, never stored as text. Episodes
   therefore keep Ollama loaded and a Claude process alive between Continues, and the engine, pool
   and provider sessions are unchanged.
4. **Casting is code, not model output** (R6). Names come from a per-language name bank matched to
   the voice's gender, and voices from the installed voices for the language. Personalities come
   from a catalogue of ten. Each language already has two installed voices, so **nothing new is
   downloaded** (R7). Each host line is spoken in its host's voice, and a missing voice is reported,
   never substituted.

What is new:
- two backend domain modules: `app/podcasts/` (catalogues, policy, cues, sanitiser, casting,
  generator, Surprise me, storage and router) and `app/conversation_summary/`;
- a third, `app/conversation_turns/`, which receives the turn mechanics `chat.py` keeps private, so
  both routers share them (R11);
- five tables and one `app_settings` column, all additive (R18);
- three new frontend screens (Podcasts, setup, episode), a shared Summary panel, a nav pill on
  Home, and podcast rows in Past Chats (R15, R17).

The real risk is model quality on `llama3.1:8b`: single-speaker discipline (SC-003), speaker
identity (SC-004), language (SC-005), level (SC-006), the generator (SC-007) and summary grounding
(SC-012). The turn-taking half of SC-002 is guaranteed by construction. The rest are measured with
the hand-run benchmark and review-sheet pattern of 003, 005 and 006 before anything is claimed
(R16).

---

## Technical Context

**Language/Version**: Python 3.12 (backend `.venv`; `requires-python >= 3.11`), TypeScript 5.4 /
React 18.3 (frontend)

**Primary Dependencies**:
- Backend: FastAPI, SQLAlchemy 2.0, `faster-whisper`, `piper-tts`, the `ollama` client
  (llama3.1), and the `claude -p` adapter (004).
- Structured output (`StructuredLLMProvider.chat_json`), which both providers already implement,
  is used for the generator and the summary.
- **No new runtime or dev dependencies.** The language and level benchmarks reuse `wordfreq`
  (005, dev extra).
- **No new voice downloads**: two installed voices per language already meet FR-030 (research R7).
- Frontend: React 18, react-router-dom v6, TanStack Query v5, Vitest + Testing Library, and
  Playwright. **No new dependencies.**

**Storage**: SQLite (WAL, foreign keys ON). Every change is additive (research R18):
- five new tables via `create_all()`: `podcast_episodes`, `podcast_hosts`, `podcast_host_lines`,
  `podcast_preferences` and `conversation_summaries`, all cascading from `conversations`;
- one `_ADDITIVE_COLUMNS` entry: `app_settings.summary_language`.

No existing row is updated, and `conversations` and `messages` gain no columns.

**Testing**:
- pytest: unit, contract and integration tests; ≥ 90% coverage.
- Seeded property tests for the turn policy (≥ 1,000 simulated episodes per format).
- The existing `benchmark` and `claude_live` markers for the hand-run checks (quickstart §3).
- Vitest for hooks and components.
- Playwright E2E, mandatory for every frontend change: three new specs, and three existing specs
  extended.

**Target Platform**: Linux desktop, local-first. Ollama, Piper and faster-whisper by default;
Claude is opt-in (004). A Panel episode with speech must work fully offline (SC-010).

**Project Type**: Web application (FastAPI backend + Vite/React frontend).

**Performance Goals**:
- ≤ 5 s at p90 from Continue until the next host line's audio is ready to play, on the default
  local setup (SC-009, "starts playing"). The warm session (R3), a cue under ~40 tokens and eager
  TTS scheduling keep this within reach. The benchmark reports the time to the text and the
  synthesis time separately.
- Summary ≤ 10 s at p90 (SC-014). Switching the summary's language is instant, because both
  versions arrive together (R13).
- A ready-made show starts in < 30 s from Home, and a Surprise me show in < 60 s (SC-001).

**Constraints**:
- FR-034 / SC-011: roleplay prompts, conversations, words, decks and settings stay unchanged. The
  roleplay prompt builders are not edited, and the chat router's tests must pass unmodified after
  the move to `conversation_turns`.
- Principle VI: no silent provider fallback, and never a voice for another language or another host.
- 006: no language code literal outside the catalogues. The existing guard test covers the new
  modules.
- Ollama's default context window on Long episodes (research R14): measured, not changed.

**Scale/Scope**:
- one learner, 2 languages, 4 installed voices;
- 3 formats, 3 lengths, 10 personalities, 8 ready-made shows;
- 18 new endpoints (17 podcast, contracts §1–§8, and 1 summary), plus 1 new settings field;
- 3 new pages and about 14 new components;
- 11 existing backend files touched beyond wiring (`factory.py`, `database.py` and `main.py`):
  - `routers/chat.py` (move out);
  - `routers/audio.py` and `routers/settings.py`;
  - `tts/selection.py` and `tts/base.py`;
  - `conversation/session.py`;
  - `practice_languages/catalog.py` and `practice_languages/__init__.py`;
  - `models/app_settings.py`;
  - `storage/base.py` with `storage/sqlite.py`.

*No NEEDS CLARIFICATION items remain. The spec's five clarifications are folded in, and the design
questions are settled in [research.md](research.md) R1–R18.*

---

## Spec interpretations

Points where the spec admits more than one reading. Each is resolved here so the choice can be
reviewed.

1. **One host: every host line invites the learner** (FR-014). With one host there is nobody else
   to talk to, so each host line ends at the learner's turn, as a roleplay reply does. Continue
   therefore appears only in Panel and Listen. The exception is the sign-off.
2. **FR-015's 25% share, FR-018's addressed host, and short episodes**:
   - the addressed host always speaks first;
   - when that widens the gap between the two hosts to 2 lines, the other host speaks next, and
     that line does not invite, so the segment runs to at least 2 lines;
   - the 25% guarantee is tested on episodes with ≥ 8 host lines, the threshold FR-015 now states. An episode the learner ends after
     three lines cannot meet a share rule, and SC-002 measures 10 learner turns.
3. **FR-014's "fourth consecutive host line"** is counted since the learner last spoke **or
   passed**. A pass restarts the count ("invite them again later", US3-5).
4. **FR-019 counts host lines only.** The wrap-up is the first host line at or after the target
   (inside the "within two lines" window). In a speaking format the wrap-up invites the learner's
   closing words, and the episode then continues until End episode (spec edge case "very long
   episode"). In Listen, the line after the wrap-up is the sign-off, which finishes the episode.
5. **FR-043 with a missing voice**: in Listen, a host whose voice is unavailable has their lines
   shown in full even with Show text off. A hidden, silent line would be empty (the "voice missing
   on resume" edge case says the episode "continues as text").
6. **FR-007 with exactly two voices per language**: shuffle changes a host's name and personality,
   and keeps their voice when no third voice is installed that differs from the other host's.
   Voices follow the host's slot. With one installed voice, both hosts share it, with the notice.
7. **FR-023, "more often than not"** is two presses in three when interests are set (seeded test:
   ≥ 60% of 300 draws). A Surprise me topic is a (seed topic, angle) pair, which is also what
   SC-008 counts as "different".
8. **FR-011**: the name the hosts use is stored on the episode and remembered in podcast
   preferences as a convenience for the next setup. Blank means "our guest".
9. **FR-027, "suggestions and the expression helper appear only at the learner's turn"**, includes
   the moment after Jump in, which makes it the learner's turn on screen.
10. **FR-035, "secondary action"**: Summary is a text button in the conversation header, in Chat
    and in episodes. It opens a non-modal panel above the transcript, so nothing in the
    conversation moves (FR-041).
11. **FR-040**: the summary language is one learner-wide setting, `summary_language`, stored as
    `conversation` or `native` rather than a language code. A German episode and a Spanish roleplay
    therefore both open in "their own language" by default.
12. **Show titles and premises are English interface text**, generated ones included, like
    scenario titles (006 interpretation 3). Only host lines and the conversation-language summary
    are in the practice language.
13. **FR-024**: suitability is judged by the model through a schema field. A blank or overlong idea
    is refused locally. There is no keyword blocklist (research R9).
14. **FR-032, "saved as they happen"**: each line is stored as it is produced, before its `line`
    frame is sent. Revealed Listen lines are stored per line.

---

## Constitution Check

*GATE: must pass before Phase 0 research. Re-checked after Phase 1 design; the result is at the
bottom of this section.*

| Principle | Status | How this design satisfies it |
|---|---|---|
| **I. Clean Code**: ≤ 20-line functions, intention-revealing names, no magic values | ✅ | Every limit is a named catalogue field: run cap, invitation deadline, hazard rates, lengths, the chunk budget and the surprise history size. The turn policy is split into one small function per rule (data-model §5). The functions the move touches are all under 20 lines already; see *Function-length plan*. |
| **II. SOLID: SRP** | ✅ | Each piece answers one question: <br>• `TurnPolicy`: who speaks and why; <br>• `render_cue`: how the model is told; <br>• `LineSanitiser`: what may be kept; <br>• `HostCaster`: who the hosts are; <br>• `ShowGenerator`: what the show is; <br>• `SurpriseTopics`: which idea to try; <br>• `EpisodeLocks`: whether a line is in progress; <br>• `Summariser`: what was said. <br>The router only sequences them. |
| **II. SOLID: OCP** | ✅ | A new format, length, personality or show is a catalogue entry, and the policy reads descriptor fields (FR-004). A new language adds names, guest labels and a sample line to its one `PracticeLanguage` entry. `SessionKind.PODCAST` and `provider_for_voice` are additions, and no existing behaviour changes. |
| **II. SOLID: LSP** | ✅ | Podcast sessions are ordinary `ConversationSession`s. No provider class changes. `provider_for_voice` raises the existing `VoiceUnavailable`. |
| **II. SOLID: ISP** | ✅ | `MessageVoiceLookup` and `SpeakerNames` are one-method consumer interfaces, declared by their consumers (audio, summary). |
| **II. SOLID: DIP** | ✅ | The audio router and the summariser depend on those interfaces. `services/factory.py` alone wires in the podcast implementations. The policy and the surprise picker take an injected `random.Random`. The generator and the summariser take `StructuredLLMProvider`. |
| **III. TDD (non-negotiable)** | ✅ | The policy, cues, sanitiser, casting and surprise picker are pure, so their tests come first, with property tests for the numeric rules. The SC-011 upgrade test is written against a frozen pre-007 schema before any migration code. The `conversation_turns` move is test-first in the strict sense: the existing chat tests are the failing-if-broken net and are not edited. |
| **≥ 90% coverage, zero skipped tests** | ✅ | Benchmarks and live checks are deselected by markers, not skipped. Voice installation, the LLM and the session provider are faked with the existing `tests/support` doubles. |
| **IV. One primary action per screen** | ✅ | Podcasts: choose a show. Setup: Start episode. Episode: Continue at the hosts' turn, Send at the learner's turn. There is exactly one at a time, and Jump in, Pass, End and Summary are secondary. Chat's primary action is unchanged. |
| **IV. Immediate feedback** | ✅ | The turn banner announces who is speaking. Continue shows a pending state, and a second press is refused with a plain 409 message. The generator shows progress and the setup screen on success. |
| **IV. Plain-language, what-to-do-next messages** | ✅ | Every 409 and 422 says what to do (contracts §3, §6, §7). The voice messages name the host and the fix. A summary that is too early says why. |
| **IV. Accessibility** | ✅ | The turn banner is `role="status"`. Hidden lines are buttons named "Show Lucía's line". The radios use `fieldset`/`legend`. Design-system tokens only. Manual check in quickstart §6. |
| **V. Compartmentalization** | ✅ | `app.podcasts` and `app.conversation_summary` each expose a package-root interface (contracts §12) and own their tables. Neither imports the other. The factory composes them through consumer interfaces. As the composition root, `services/factory.py` is the one module allowed to import their storage, lock, caster and surprise implementations, as it already does for flashcards and corrections. A boundary test enforces that no other module does. The conversations router does not learn about podcasts: Past Chats merges podcast labels client-side (R17). |
| **V. Abstractions before implementations** | ✅ | `MessageVoiceLookup`, `SpeakerNames`, `PodcastStorage` (ABC) and `SummaryStorage` (ABC) are declared and tested with fakes before the SQLite and podcast implementations. |
| **V. No feature-flag / if-debug guards** | ✅ | Format behaviour is descriptor data, not `if format == "panel"` branches. The language-literal guard now also covers the new modules. |
| **VI. Provider independence** | ✅ | Episodes and summaries work on every provider through the factory (FR-033), and no concrete provider is imported. Provider failures reach the learner as the provider's own message, with a retry. Nothing switches provider. Nothing new leaves the machine on the local stack. A host's voice is never replaced (FR-031). |
| **Playwright E2E for frontend changes** | ✅ | New `podcasts.spec.ts`, `podcast-episode.spec.ts` and `conversation-summary.spec.ts`; `home`, `history` and `chat` specs extended; fixtures added (contracts §13). |
| **Linting (ruff, black, ESLint, Prettier)** | ✅ | No tooling change. |

**Initial gate: PASS**, with three Complexity Tracking items: long React pages that each gain one
element or one merged query.

### Function-length plan (Boy Scout, quality gate)

Measured on `007-podcast-mode` @ `5897b32`. This feature touches no existing function that is over
20 lines. The functions it modifies or moves, with their current lengths:

| Function | Today | Change |
|---|---|---|
| `_relay_engine_reply` (15), `_save_learner_message` (12), `_turn_context` (16), `_plan_turn_failing_open` (9), `_persist_feedback` (7), `_feedback_frame` (8), `_schedule_tts` (10), `_start_warming` (9), `_warm_quietly` (6), `_is_low_confidence` (5), `_sse` (2), `_last_character_line` (2), `_tts_cache_dir` (2), and the `_EngineTurn`, `_SavedReply`, `_Corrections` classes ([chat.py](../../backend/app/routers/chat.py)) | as listed | **Moved** to `app/conversation_turns/`, with no behaviour changes (research R11). Only call sites of renamed functions change inside the moved bodies |
| `_languages_of` ([chat.py](../../backend/app/routers/chat.py)) | 3 | Stays in `chat.py`, which still uses it. `conversation_turns/corrections.py` gets a private copy of the same one-line wrapper |
| `get_tts_audio` ([audio.py](../../backend/app/routers/audio.py)) | 16 | The voice choice moves into a new `_speech_provider(speech, voices, message, conversation)`. `_synthesize_and_cache` takes a provider instead of a language. Both stay ≤ 20 |
| `_to_response` ([settings.py](../../backend/app/routers/settings.py)) | 14 | +1 field → 15 |
| `_settings_to_record` ([sqlite.py](../../backend/app/services/storage/sqlite.py)) | 14 | +1 field → 15 |
| `init_db` ([database.py](../../backend/app/database.py)) | 14 | +2 model imports → 16 |
| `SpeechForLanguage` ([selection.py](../../backend/app/services/tts/selection.py)) | `provider_for` 5 | `provider_for_voice` is new (≈ 8). `provider_for` is unchanged |

New code is written to the limit from the start. The podcast router's endpoints delegate to an
`EpisodeTurns` service object, as `_RoleplayContext` does for chat.

### Post-Phase-1 re-evaluation: **PASS**

The design added nothing that weakens a row above:
- the contracts confirm that no LLM, STT or TTS provider class and no roleplay prompt template
  changes. The engine gains one enum member, and TTS gains one method and one consumer interface;
- the data model confirms that every schema change is additive and cascades from `conversations`,
  and that no core table gains a column;
- the quickstart gives every Principle IV claim and every success criterion a concrete check;
- research R11 **removes** a would-be duplication of the correction flow instead of adding one.

---

## Project Structure

### Documentation (this feature)

```text
specs/007-podcast-mode/
├── spec.md                    # input
├── plan.md                    # this file
├── research.md                # Phase 0: R1–R18
├── data-model.md              # Phase 1
├── quickstart.md              # Phase 1
├── contracts/
│   └── api.md                 # Phase 1
├── checklists/
│   └── requirements.md        # from /speckit-specify
├── speaker-review-sheet.md    # created during validation (SC-004)
├── summary-review-sheet.md    # created during validation (SC-012, SC-013)
└── tasks.md                   # Phase 2 (/speckit-tasks; NOT created here)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── podcasts/                           # NEW domain module
│   │   ├── __init__.py                     # public: router, PODCAST_SCENARIO_ID,
│   │   │                                   #   PodcastMessageVoices, PodcastSpeakerNames
│   │   ├── catalog.py                      # formats, lengths, personalities, ready-made shows
│   │   ├── models.py                       # podcast_episodes, podcast_hosts, podcast_host_lines,
│   │   │                                   #   podcast_preferences
│   │   ├── schemas.py                      # ShowDraft, EpisodeResponse, line frame, preferences
│   │   ├── prompts.py                      # standing prompt, render_cue, generator prompt + schema
│   │   ├── router.py                       # /api/podcasts/* (contracts §1–§8)
│   │   └── services/
│   │       ├── turn_policy.py              # TurnPolicy, EpisodeState, LineCue (pure)
│   │       ├── cues.py                     # saved-history builder: lines + re-rendered cues
│   │       ├── sanitiser.py                # LineSanitiser (pure)
│   │       ├── casting.py                  # HostCaster: names, voices, personalities
│   │       ├── generator.py                # ShowGenerator (structured output)
│   │       ├── surprise.py                 # SurpriseTopics + RecentSurprises
│   │       ├── episode_turns.py            # EpisodeTurns: one line end to end
│   │       ├── episode_lock.py             # EpisodeLocks (non-blocking, per episode)
│   │       ├── speaker_views.py            # PodcastMessageVoices, PodcastSpeakerNames
│   │       ├── storage.py                  # PodcastStorage ABC + records
│   │       └── sqlite_storage.py
│   ├── conversation_summary/               # NEW domain module
│   │   ├── __init__.py                     # public: router, SpeakerNames
│   │   ├── models.py                       # conversation_summaries
│   │   ├── prompts.py                      # summary prompt + JSON schema
│   │   ├── router.py                       # GET /api/conversations/{id}/summary
│   │   └── services/                       # summariser (fold, parse, cache), storage ABC + SQLite
│   ├── conversation_turns/                 # NEW: moved from routers/chat.py (research R11)
│   │   └── __init__.py, relay.py, learner.py, corrections.py, speech.py
│   ├── practice_languages/catalog.py       # + host_names, guest_labels, sample_line
│   ├── practice_languages/__init__.py      # + host_names_for, guest_labels_for, voice_sample_line
│   ├── services/
│   │   ├── conversation/session.py         # + SessionKind.PODCAST
│   │   ├── tts/base.py                     # + MessageVoiceLookup
│   │   ├── tts/selection.py                # + provider_for_voice
│   │   ├── storage/base.py, sqlite.py      # + summary_language on AppSettingsRecord
│   │   └── factory.py                      # + podcast/summary wiring
│   ├── models/app_settings.py              # + summary_language
│   ├── routers/chat.py                     # imports conversation_turns; no behaviour change
│   ├── routers/audio.py                    # host voice via MessageVoiceLookup
│   ├── routers/settings.py                 # + summary_language
│   ├── database.py                         # + model imports, + 1 _ADDITIVE_COLUMNS entry
│   └── main.py                             # + podcasts and summary routers
│   # NOT modified: prompts/templates.py, corrections/*, conversation_levels/*,
│   #   services/llm/*, services/conversation/{engine,pool,sync}.py, services/stt/*,
│   #   routers/{conversations,learning,vocabulary,scenarios}.py, flashcards/*
└── tests/
    ├── unit/podcasts/                      # catalogue P1–P7, turn policy + properties, cues,
    │                                       #   sanitiser, casting, generator, surprise, prompts budget
    ├── unit/conversation_summary/          # parser, fold, speaker labels, prompt
    ├── contract/                           # podcasts catalogue, episode, summary shapes; storage ABCs
    ├── integration/
    │   ├── podcasts/                       # episode lifecycle per format, sessions and rebuilds,
    │   │                                   #   corrections, locks, voices, upgrade (SC-011),
    │   │                                   #   *_benchmark.py (hand-run, quickstart §3)
    │   ├── conversation_summary/           # cache, isolation (FR-041), roleplay + episode,
    │   │                                   #   test_summary_benchmark.py
    │   └── routers/                        # audio (host voice), settings (summary_language)
    ├── live/test_claude_code_live.py       # + podcast Panel check (claude_live)
    ├── support/scripted_line_writer.py     # NEW: session provider that returns scripted lines
    └── fixtures/schema_006.sql             # NEW: frozen pre-007 schema for SC-011

frontend/
├── src/
│   ├── App.tsx                             # + /podcasts, /podcasts/setup, /podcasts/episodes/:id
│   ├── services/podcastsApi.ts             # NEW: catalogue, preferences, generate, surprise,
│   │                                       #   shuffle, episodes, SSE actions, reveal
│   ├── services/api.ts                     # + getConversationSummary, summary_language
│   ├── hooks/podcasts/                     # NEW: usePodcastCatalog, usePodcastPreferences,
│   │                                       #   usePodcastEpisode (turn state machine), useShowDraft
│   ├── hooks/useConversationSummary.ts     # NEW (shared by Chat and episodes)
│   ├── components/podcasts/                # NEW: ShowCard, ShowGenerator, InterestsEditor,
│   │                                       #   FormatFieldset, LengthFieldset, HostCard,
│   │                                       #   LearnerNameField, HostLine, EpisodeControls,
│   │                                       #   TurnBanner, ShowTextSwitch, PodcastLabel
│   ├── components/chat/SummaryButton.tsx, SummaryPanel.tsx   # NEW (shared)
│   └── pages/
│       ├── Podcasts.tsx, PodcastSetup.tsx, PodcastEpisode.tsx # NEW
│       ├── Chat.tsx                        # + <SummaryButton> in the header
│       ├── Home.tsx                        # + Podcasts nav pill
│       └── History.tsx                     # + podcast label and link per row
└── e2e/
    ├── podcasts.spec.ts, podcast-episode.spec.ts, conversation-summary.spec.ts   # NEW
    ├── fixtures.ts                         # + podcast and summary fixtures
    └── home, history, chat specs           # extended
```

**Structure Decision**: keep the existing web-application layout (`backend/app`, `frontend/src`).
- `podcasts/` follows the flashcards reference pattern: own models, schemas, router, and
  `services/` behind a storage ABC.
- `conversation_summary/` has the same shape at a smaller size.
- `conversation_turns/` is a shared service package with no tables and no router, like
  `conversation_levels/`.
- Frontend: podcast hooks go in `hooks/podcasts/`, as `hooks/flashcards/` does. The summary UI is
  shared from `components/chat/`, because both the Chat page and episodes use it.
- Colocated `*.test.tsx` files follow the existing convention and are left out of the tree.

### Suggested phase order (for `/speckit-tasks`)

1. **Foundation**, which blocks every story:
   - the frozen `schema_006.sql` and the SC-011 upgrade test, written first;
   - the move of chat.py's turn mechanics into `conversation_turns/`, with the chat tests green and
     unedited;
   - the catalogues (formats, lengths, personalities, shows) with invariants P1–P7;
   - the `PracticeLanguage` additions;
   - the models and tables, the `PodcastStorage` ABC and its SQLite implementation;
   - `SessionKind.PODCAST`, `MessageVoiceLookup` and `provider_for_voice`, with the audio router
     using the lookup;
   - `TurnPolicy` with its property tests, `render_cue` and the history builder, `LineSanitiser`,
     and `HostCaster`;
   - the factory wiring, `EpisodeLocks`, and the `scripted_line_writer` test double.
2. **US1 (P1): One host, the MVP**:
   - the catalogue endpoint and the preferences endpoint (last format and learner name only);
   - episode creation and GET, and `/next`, `/message` and `/end` with corrections;
   - warm session, suggestions, and TTS in the host's voice;
   - the Past Chats list endpoint;
   - frontend: the Podcasts screen (show cards only), setup (format and length), the episode page
     with the input bar and learning tools, the Home pill, the History label, and E2E.

   **Run the SC-005 and SC-006 benchmarks here**, before more is built on host-line quality.
3. **US2 (P1): Listen**:
   - the two-host policy paths without the learner, and the sign-off finishing the episode;
   - reveal, Show text in preferences, and `HostLine`'s hidden state;
   - voiceless-host lines shown in full;
   - the shared-voice and no-voice notices on the catalogue and setup screen (spec edge case
     "fewer than two voices"). Listen is the first two-host format, so the notices ship here;
   - E2E, and the SC-003 benchmark on Listen.
4. **US6 (P2): Summary**, which is independent of US2–US5:
   - the `conversation_summary` module, `summary_language`, `PodcastSpeakerNames`;
   - `SummaryButton` and `SummaryPanel` in Chat and episodes;
   - E2E, and the SC-012–SC-014 review and benchmark.
5. **US3 (P2): Panel**:
   - Jump in, Pass, the addressed host, and the settle invitation;
   - `EpisodeControls` and `TurnBanner`;
   - E2E, and the SC-002 and SC-003 benchmarks on Panel.
6. **US4 (P2): Generator and Surprise me**:
   - `ShowGenerator`, the decline path, and Another version;
   - `SurpriseTopics` with interests, and `InterestsEditor`;
   - E2E, and the SC-007 and SC-008 benchmark.
7. **US5 (P3): Shaping hosts**:
   - shuffle, the personality select, and the voice sample;
   - E2E, and the SC-004 review sheet.
8. **Polish**:
   - `docs/architecture.md`: the podcast and summary modules, and "Open items" for any benchmark
     result below its bar and for the R14 context measurement;
   - `README.md`: the Podcasts section;
   - `CLAUDE.md` Recent Changes;
   - the manual accessibility check, and the quickstart run including SC-010 and SC-011.

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| `Chat` (~520 lines) in `frontend/src/pages/Chat.tsx` stays over 20 lines while this feature adds a `<SummaryButton conversationId={convId} />` to its header | The change is one self-contained element that loads its own data (`useConversationSummary`) and holds its own open/closed state. `Chat` gains no state, effects or handlers. | Splitting `Chat` is the frontend refactor that 004, 005 and 006 already recorded as a follow-up (`useChatStream`, `useRecorderFlow`). Doing it here would put E2E risk unrelated to podcasts across the roleplay screen that FR-034 says must not change. |
| `History` (~175 lines) in `frontend/src/pages/History.tsx` stays over 20 lines while this feature adds a podcast label and link per row | The page gains one query hook (`usePodcastEpisodeIndex`) and swaps a row's link target and label through a `PodcastLabel` component. The merge logic lives in the hook, not the page. | Splitting the page into row components is the same recorded follow-up. The change here is two lines of JSX. |
| `Home` (~270 lines) in `frontend/src/pages/Home.tsx` stays over 20 lines while this feature adds a "Podcasts" nav pill | One `<Link>` element next to the existing three pills. | Same as above. The page's logic is untouched. |
