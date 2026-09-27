# Implementation Plan: German Language Support

**Branch**: `006-german-language-support` | **Date**: 2026-09-26 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/006-german-language-support/spec.md`

---

## Summary

Make the practice language selectable, **Spanish** (the default) or **German**, as one learner-wide
setting. A conversation keeps the language it started with. Every conversation feature works in
German, speech is transcribed and spoken in the conversation's language, and flashcards show only
the selected language's words, decks and statistics.

Most of the groundwork already exists, which keeps the change contained:
- **Languages are already stored.** `app_settings.target_language`, `conversations.target_language`,
  `vocabulary_items.target_language` (with `UNIQUE(word, target_language)`) and
  `word_llm_cache.language` all exist and all hold `es` today. The practice language *is* the
  existing `app_settings.target_language` (research R1).
- **Every prompt builder already takes the language as a parameter**, so no prompt template is
  edited. What changes is what the routers pass: the conversation's language, as a name ("German")
  rather than a code (`de`). Today the prompts literally say "write EXCLUSIVELY in es", and the
  learner-visible repeat request says "speak clearly in es" (research R2).

What is new:
- a `backend/app/practice_languages/` domain module: the catalogue (FR-005), naming, and voice
  resolution;
- two German Piper voices, fetched by `run.sh --setup`;
- a `voice_choices` table (one remembered voice per language) with a one-time seed from the legacy
  `tts_voice` column;
- language-aware TTS behind a new `SpeechForLanguage` abstraction, with a plain 503 and never a
  cross-language fallback;
- two additive columns: `decks.target_language` and `practice_sessions.target_language`;
- one read-only endpoint, `GET /api/settings/practice-languages`;
- UI:
  - a Practice-language fieldset on Settings;
  - a note on Home;
  - a language tag and a voice notice in Chat;
  - language labels in Past Chats;
  - a language-keyed query layer for Flashcards.

Two latent bugs are fixed on the way because FR-009 requires it:
- alternative phrasing reads the *setting's* language;
- `Chat.tsx` sends the *setting's* language for transcription and word lookup.

After this feature, every learning aid derives its language on the server from the conversation it
belongs to (research R9).

The real risks are model quality, and both are measured before anything is claimed:
- German adherence on `llama3.1:8b` (SC-002);
- Whisper `base` accuracy on German (SC-003).

Both use the hand-run benchmark pattern of 003 and 005 (research R8, R14).

---

## Technical Context

**Language/Version**: Python 3.12 (backend `.venv`; `requires-python >= 3.11`), TypeScript 5.4 /
React 18.3 (frontend)

**Primary Dependencies**:
- Backend: FastAPI, SQLAlchemy 2.0, `faster-whisper` (already multilingual), `piper-tts`, the
  `ollama` client (llama3.1), and the `claude -p` adapter (004).
- **No new runtime or dev dependencies.** The SC-002 benchmark reuses `wordfreq` 3.1.1, which 005
  added to the dev extra.
- New *data* dependencies: two Piper voice models (`de_DE-thorsten-medium`, `de_DE-kerstin-low`,
  63 MB each). Both were verified in the upstream `rhasspy/piper-voices` index on 2026-09-26 and are
  downloaded by `run.sh` (research R4).
- Frontend: React 18, react-router-dom v6, TanStack Query v5, Vitest + Testing Library, and
  Playwright. **No new dependencies.**

**Storage**: SQLite (WAL, foreign keys ON). All changes are additive (research R13):
- one new table, `voice_choices`, via `create_all()`;
- two `_ADDITIVE_COLUMNS` entries, `decks.target_language` and `practice_sessions.target_language`,
  both `VARCHAR(20) NOT NULL DEFAULT 'es'`;
- one idempotent `INSERT OR IGNORE` seed in `_migrate_db()`.

No existing row is updated.

**Testing**:
- pytest: unit, contract and integration; ≥ 90% coverage; the existing `benchmark` marker for the
  two hand-run benchmarks (SC-002, SC-003).
- Vitest for hooks and components.
- Playwright E2E, mandatory for every frontend change (new `practice-language.spec.ts`, which holds
  the Chat language checks, and six existing specs extended).

**Target Platform**: Linux desktop, local-first. Ollama, Piper and faster-whisper by default;
Claude is opt-in (004). German must work fully offline after setup (SC-007).

**Project Type**: Web application (FastAPI backend + Vite/React frontend).

**Performance Goals**:
- No added round trips on a chat turn.
- The TTS voice is resolved from the already-loaded settings record plus one file-existence check.
- The Flashcards pages make the same number of requests; they carry one extra query parameter.
- Switching language costs nothing at switch time. The next new conversation simply starts in the
  new language.

**Constraints**:
- FR-018 / Principle VI: never speak text with another language's voice, and never fall back
  silently.
- FR-024 / FR-025: upgrading and switching never rewrite existing data.
- 005's Natural byte-identity property is untouched (the renderers do not change).

**Scale/Scope**:
- one learner, 2 languages, 4 voices;
- 12 prompt call sites now receive names;
- 5 learning-aid endpoints move to server-derived languages;
- 8 flashcard storage methods gain a `language` keyword;
- 7 frontend pages or components are touched.

*No NEEDS CLARIFICATION items remain. The spec had none, and the design questions are settled in
[research.md](research.md) R1–R15.*

---

## Spec interpretations

Points where the spec admits more than one reading. Each is resolved here so the choice can be
reviewed.

1. **FR-015, "voices for the selected practice language"**, means the language currently selected in
   the Settings **form**, before saving. The learner can pick German and a German voice in one Save.
   On a language change the form pre-selects that language's remembered voice. The server rejects a
   voice that does not match the language being saved, with a 422 (contracts §2).
2. **FR-011, "labels that name the practice language … MUST name the conversation's language"**,
   covers:
   - the expression-helper direction label ("English → German");
   - the chat-header language tag;
   - the Past Chats language label.

   The only place that names the *setting's* language is the Home note (FR-004) and the Settings
   fieldset. The rest of the UI stays English with no language names.
3. **FR-008, "conversation titles"**, is met without change:
   - scenario titles are English catalogue text;
   - custom-scenario titles are generated in English, because they are interface text (FR-011).

   Neither depends on the practice language, so there is no German-specific behaviour to add.
4. **FR-018 is surfaced in three places**, and two of them say the same thing:
   - one persistent notice per German conversation, with no per-reply errors;
   - the flashcard play button's failure text;
   - a hint under the Settings voice field.

   The chat notice and the flashcard text carry the same backend-generated sentence
   (`voice_unavailable_message`), so they cannot drift apart.

   The Settings hint is different by necessity. It describes **one voice**, not a language. If
   Kerstin is missing while Thorsten is installed, German as a whole is still speakable, so the
   per-language sentence would be wrong there. The hint is therefore a short per-voice status
   ("Not installed. Run ./run.sh --setup to download it."), driven by `VoiceResponse.is_installed`
   (contracts §3, §10).
5. **FR-020, "statistics count only German practice"**, includes the streak and "sessions this week".
   A day with only Spanish practice does not extend the German streak.
6. **SC-002, "no English or Spanish words"**, does not count proper nouns (Berlin, Maria) or
   international loanwords that are standard German (Hotel, Taxi, Ticket, OK) as foreign words. The
   benchmark's allow-list is short and reviewed (research R8).
7. **The spec's "Chat header" edge case** ("shows the conversation's language but offers no control")
   is a text tag, not a disabled control. A disabled `<select>` would suggest the value can change.
8. **The spec's "Language changed during a flashcard session" edge case** is met because
   session-bound endpoints use the session's own language (research R10.3). The practice page is
   never re-scoped by the setting.
9. **FR-017, "at least one German voice … without an internet connection"**, is met by setup-time
   download (spec Assumptions: "a German voice is fetched once during setup"). An invariant test
   fails if a catalogue voice is missing from `run.sh` (data-model I4).

---

## Constitution Check

*GATE: must pass before Phase 0 research. Re-checked after Phase 1 design; the result is at the
bottom of this section.*

| Principle | Status | How this design satisfies it |
|---|---|---|
| **I. Clean Code**: ≤ 20-line functions, intention-revealing names, no magic values | ✅ | Language codes, names, default voices and the unavailable message are named catalogue data in one module. Touched functions over the limit are brought under it; see *Function-length plan* below. The four learning endpoints' duplicated `nonlocal computed` closure is extracted once (three or more repetitions). |
| **II. SOLID: SRP** | ✅ | The catalogue says *which* languages exist. `ConversationLanguages` says *how a language is named* in prompts. `voice_for` says *which voice* a language uses. `SpeechForLanguage` says *whether and how* to speak. Routers say *which conversation* a request belongs to. |
| **II. SOLID: OCP** | ✅ | A third language is one `PracticeLanguage` entry, its `VoiceInfo` entries and its `run.sh` keys, with no feature-code change (FR-005, research R3). No prompt template is edited (research R2). |
| **II. SOLID: LSP** | ✅ | `TTSProvider`, `STTProvider`, `LLMProvider` and the session providers keep their contracts. `VoiceUnavailable` subclasses the existing `TTSError`, so existing `TTSError` handling still catches it. |
| **II. SOLID: ISP** | ✅ | `VoiceInstallation` is a one-method ABC. `StorageProvider` gains one method (`save_voice_choice`). The flashcard storage ABC gains a keyword on existing methods, not new methods. |
| **II. SOLID: DIP** | ✅ | Routers depend on `SpeechForLanguage`, injected by `services/factory.py`, which alone names Piper. `AnalyticsService` is given its language; it never reads settings. The flashcards module does not import app settings at all: the language arrives as a request parameter (research R10). |
| **III. TDD (non-negotiable)** | ✅ | The catalogue invariants (I1–I6), `ConversationLanguages`, `voice_for` and the seed are pure or DB-local, and are testable before any wiring. Every task in `tasks.md` will lead with its failing test. The SC-005 preservation test is written against a pre-006 fixture before the migration code exists. |
| **≥ 90% coverage, zero skipped tests** | ✅ | The two benchmarks are *deselected* by the existing `-m 'not benchmark …'` addopts, not skipped. Voice installation is faked in tests, so no test depends on voice files. |
| **IV. One primary action per screen** | ✅ | Settings: the primary action stays Save, and the language is one more fieldset. Home: the primary action stays starting a scenario, and the language note is secondary text with a link. Chat: the language tag is static text. |
| **IV. Immediate feedback** | ✅ | The form's voice list swaps as soon as the language radio changes. The Save success message is unchanged. The Home note updates on the next visit. |
| **IV. Plain-language, what-to-do-next messages** | ✅ | The voice message says what happened and what to do ("Run ./run.sh --setup … You can keep practising in text"). The 422s say which voice or language to pick (contracts §2, §8). |
| **IV. Accessibility** | ✅ | Native radio inputs in a `<fieldset>`/`<legend>`. The voice notice is `role="status"`. Tags use design-system tokens (`--color-text-muted`, `--radius-lg`) with no hardcoded colours. There is a manual check in quickstart §5. |
| **V. Compartmentalization** | ✅ | `app.practice_languages` exposes an eight-name interface (contracts §9). Routers, flashcards and corrections import only its package root. It owns no tables. `voice_choices` belongs to settings storage, like `app_settings`. |
| **V. Abstractions before implementations** | ✅ | `VoiceInstallation` and `SpeechForLanguage` are declared, and tested with fakes, before `PiperVoiceInstallation` is written. |
| **V. No feature-flag / if-debug guards** | ✅ | No code branches on `"de"` or `"es"`. Every language difference is catalogue data. A test greps `backend/app` and `frontend/src` (excluding the catalogue, the voice catalogue and test files) for the quoted literals `'es'`, `"es"`, `'de'` and `"de"`. The one existing hit, `AppSettings.target_language`'s `default="es"`, is changed to `DEFAULT_PRACTICE_LANGUAGE`. |
| **VI. Provider independence** | ✅ | No LLM, STT or TTS provider class changes contract. TTS selection goes through a factory-built abstraction. A missing voice is reported, never replaced (**no silent fallback**). German works identically on Ollama and Claude, and selecting German never changes the provider (FR-026). Nothing new leaves the machine. |
| **Playwright E2E for frontend changes** | ✅ | New `practice-language.spec.ts` (Settings, Home, Chat and voice-missing journeys); `settings`, `home`, `history`, `flashcards`, `flashcard-practice` and `flashcard-analytics` specs extended; new fixtures (contracts §10). |
| **Linting (ruff, black, ESLint, Prettier)** | ✅ | No tooling change. |

**Initial gate: PASS**, with two recorded Complexity Tracking items (long React page components that
gain a single hook call or element).

### Function-length plan (Boy Scout, quality gate)

Measured on `006-german-language-support` @ `3144321`. These are the functions this feature modifies
that are over 20 lines, or that its change would push over.

| Function | Today | Plan |
|---|---|---|
| `grammar_check`, `translate`, `alternative_phrasing`, `word_lookup` ([learning.py](../../backend/app/routers/learning.py)) | 19, 18, 20, 20 | Adding language resolution pushes all four over. Extract `_cached_llm_result(storage, llm, CachedToolRequest)`, the fourth copy of the `nonlocal computed` closure, and resolve languages in `conversation_languages_for_message`. Each endpoint becomes about 8 lines. |
| `get_tts_audio` ([audio.py](../../backend/app/routers/audio.py)) | 24 | Extract `_cached_wav(path)` and `_synthesize_and_cache(speech, message, conversation)`. |
| `transcribe_audio` (audio.py) | 39 | Extract `_require_supported_language(language)`, `_wav_from_upload(file)` and `_transcribe_off_loop(stt, wav, language)`. |
| `save_vocabulary` ([vocabulary.py](../../backend/app/routers/vocabulary.py)) | 24 | Extract `_word_languages(storage, req, app_settings)` and `_save_response(item)`. |
| `get_words` ([flashcards/router.py](../../backend/app/flashcards/router.py)) | 27 | Extract `_word_list_item(record)`, which also removes the duplicate in `patch_word_classification`. |
| `get_vocab_tts` (flashcards/router.py) | 25 | Extract `_cached_word_audio(word)` and `_synthesize_word(speech, word)`. |
| `create_deck` (flashcards/router.py) | 47 | Extract `_deck_word_pool(body, storage)`, `_require_same_language(words, language)` (the 422) and `_deck_name(body, now)`. |
| `list_decks` (flashcards/router.py) | 19 | Adding the language pushes it over. Extract `_deck_summary(deck, storage)`, which is shared with `update_deck_name`. |
| `refresh_deck` (flashcards/router.py) | 32 | Extract `_learned_card_ids(cards, storage)` and `_refresh_candidates(deck, cards, storage)`. |
| `create_missed_deck` (flashcards/router.py) | 41 | Extract `_missed_word_ids(results)` and `_missed_deck_cards(ids)`. |
| `hardest_words` ([analytics.py](../../backend/app/flashcards/services/analytics.py)) | 29 | Extract `_tally_by_word(results)` and `_hardest_candidate(vocab_id, counts)`. |
| `SQLiteFlashcardStorageProvider.create_deck` ([sqlite_storage.py](../../backend/app/flashcards/services/sqlite_storage.py)) | 33 | Extract `_insert_cards(deck_id, cards)`. |
| `SQLiteFlashcardStorageProvider.list_words` (sqlite_storage.py) | 18 | Adding the filter pushes it over. Extract `_filtered_word_query(filters)`. |
| `SQLiteFlashcardStorageProvider.create_session` (sqlite_storage.py) | 18 | The deck-language lookup pushes it over. Extract `_deck_language(deck_id)`. |
| `AudioControls` ([AudioControls.tsx](../../frontend/src/components/flashcards/AudioControls.tsx)) | 52 | Extract a `useWordAudio(url)` hook (play state and failure detail) and an `AudioFailureMessage` component. |

These functions gain a parameter or a line and stay under the limit:
- `_standing_roleplay_prompt` (13), `_turn_context` (15), `_helper_turn_request` (13) and
  `_schedule_tts` (10) in `chat.py`;
- `_conv_response` (13) in `conversations.py`;
- `_to_response` (14) and `get_voices_endpoint` (12) in `settings.py`;
- `_settings_to_record` (14) in `sqlite.py`;
- `_calculate_streak` (17), `_snapshot_classifications` (10) and every other `AnalyticsService`
  method.

`create_conversation` (33) and `start_session` (21) are **not modified**: the conversation is still
stamped from the setting, and the session's language is copied inside storage.

### Post-Phase-1 re-evaluation: **PASS**

The design added nothing that weakens a row above:
- the contracts confirm that no LLM or STT provider class and no prompt template changes. The TTS
  change is a new abstraction around the unchanged `PiperTTSProvider` (Principle VI);
- the data model confirms that every schema change is additive, and that the new ORM columns have no
  silent default (FR-021 comes from the `ALTER TABLE` default, not from code);
- the quickstart gives every Principle IV claim and every SC a concrete check.

Research R9 *removes* client-trusted language fields, and the function-length plan retires 11
existing violations.

---

## Project Structure

### Documentation (this feature)

```text
specs/006-german-language-support/
├── spec.md              # input
├── plan.md              # this file
├── research.md          # Phase 0: R1–R15
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── api.md           # Phase 1
├── checklists/
│   └── requirements.md  # from /speckit-specify
└── tasks.md             # Phase 2 (/speckit-tasks; NOT created here)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── practice_languages/                 # NEW domain module: no tables, no router
│   │   ├── __init__.py                     # public: PracticeLanguage, PRACTICE_LANGUAGES,
│   │   │                                   #   DEFAULT_PRACTICE_LANGUAGE, UnknownLanguage,
│   │   │                                   #   language_name, ConversationLanguages, voice_for,
│   │   │                                   #   voice_unavailable_message
│   │   ├── catalog.py                      # PracticeLanguage, PRACTICE_LANGUAGES, native names
│   │   ├── naming.py                       # language_name, ConversationLanguages
│   │   └── voices.py                       # voice_for, voice_unavailable_message
│   ├── models/voice_choice.py              # NEW: VoiceChoice ORM model
│   ├── models/app_settings.py              # tts_voice marked legacy (comment only)
│   ├── database.py                         # + 2 _ADDITIVE_COLUMNS, + _seed_voice_choices, + model import
│   ├── main.py                             # + VoiceUnavailable → 503 handler
│   ├── services/
│   │   ├── storage/base.py                 # AppSettingsRecord.voice_choices; + save_voice_choice
│   │   ├── storage/sqlite.py               # load choices; upsert choice
│   │   ├── tts/base.py                     # + VoiceUnavailable, + VoiceInstallation
│   │   ├── tts/piper.py                    # + PiperVoiceInstallation
│   │   ├── tts/selection.py                # NEW: SpeechForLanguage
│   │   ├── tts/voices.py                   # + VoiceInfo.language, + German voices, + voices_for
│   │   └── factory.py                      # get_tts → get_speech_for_language, + get_voice_installation
│   ├── routers/
│   │   ├── settings.py                     # + practice-languages endpoint; validation; voice per language
│   │   ├── conversations.py                # + *_language_name fields
│   │   ├── chat.py                         # names via ConversationLanguages; helper by conversation_id;
│   │   │                                   #   TTS per conversation language
│   │   ├── learning.py                     # languages from message → conversation; _cached_llm_result
│   │   ├── audio.py                        # language validation; TTS by conversation language; 503
│   │   └── vocabulary.py                   # language from source conversation
│   ├── flashcards/
│   │   ├── models.py                       # + Deck.target_language, PracticeSession.target_language
│   │   ├── schemas.py                      # + language on DeckConfigRequest; + target_language on deck responses
│   │   ├── router.py                       # required ?language=; session-language endpoints; TTS by word
│   │   └── services/                       # storage ABC/SQLite language keyword; AnalyticsService(language);
│   │                                       #   SessionService uses session language; llm_cache names
│   │   # NOT modified: prompts/templates.py, corrections/prompts.py, services/llm/*,
│   │   #   services/conversation/*, services/stt/*, conversation_levels/*, services/scenario/*
└── tests/
    ├── unit/practice_languages/            # catalogue invariants I1–I6, naming, voice_for
    ├── unit/services/                      # selection (SpeechForLanguage), Piper installation, voices
    ├── contract/                           # practice-languages response shape; storage ABC contracts
    └── integration/
        ├── practice_languages/
        │   ├── test_upgrade_preserves_data.py    # SC-005, pre-006 fixture, init_db ×2
        │   ├── test_conversation_language.py     # FR-006/009/013/014/019 across a switch
        │   ├── test_language_in_prompts.py       # names not codes, all call sites
        │   ├── test_flashcards_by_language.py    # SC-006 mixed fixtures; in-progress session
        │   ├── german_evaluation_set.py          # 10 scenarios × 5 turns; 20 dictation sentences
        │   ├── test_german_benchmark.py          # @benchmark SC-002
        │   └── test_transcription_benchmark.py   # @benchmark SC-003
        └── routers/                              # existing settings/audio/learning/vocabulary tests extended
    ├── support/fake_speech.py              # NEW: FakeVoiceInstallation, RecordingTtsBuilder, override_speech;
    │                                       #   replaces every get_tts / PiperTTSProvider test double
    └── fixtures/schema_005.sql             # NEW: frozen pre-006 schema for the SC-005 upgrade tests

run.sh                                      # + de_DE-thorsten-medium, de_DE-kerstin-low in PIPER_VOICES

frontend/
├── src/
│   ├── services/api.ts                     # + PracticeLanguageOption, getPracticeLanguages();
│   │                                       #   Conversation *_name fields; learning/helper args trimmed
│   ├── services/flashcardsApi.ts           # language on fetchWords/listDecks/createDeck/fetchAnalytics;
│   │                                       #   describeAudioFailure(url)
│   ├── hooks/
│   │   ├── usePracticeLanguages.ts         # NEW: catalogue + current practice language (shared)
│   │   └── flashcards/                     # NEW: useWordLibrary, useDecks, useFlashcardAnalytics
│   │                                       #   (language in request and query key)
│   ├── components/settings/
│   │   ├── PracticeLanguageFieldset.tsx    # NEW
│   │   ├── TtsVoiceField.tsx               # + not-installed hint
│   │   └── useSettingsForm.ts              # + practiceLanguage; language change swaps voice
│   ├── components/home/PracticeLanguageNote.tsx        # NEW (FR-004)
│   ├── components/chat/
│   │   ├── useConversationLanguage.ts      # NEW: codes and names from the conversation
│   │   ├── ConversationLanguageTag.tsx     # NEW (header)
│   │   ├── VoiceUnavailableNotice.tsx      # NEW (FR-018)
│   │   ├── ExpressionHelperPanel.tsx       # names in label; conversationId to API
│   │   └── MessageBubble.tsx, LearningToolPanel.tsx   # language props removed
│   ├── components/flashcards/AudioControls.tsx         # failure detail; split (function-length plan)
│   └── pages/                              # Settings, Home, Chat, History, Flashcards, FlashcardDecks,
│                                           #   FlashcardAnalytics: one hook or element each
└── e2e/
    ├── practice-language.spec.ts           # NEW
    ├── fixtures.ts                         # + language fixtures; codes, not names
    └── settings, home, history, flashcards, flashcard-practice, flashcard-analytics specs  # extended
```

**Structure Decision**: the existing web-application layout (`backend/app`, `frontend/src`). The new
backend catalogue is a sibling domain module, patterned on `conversation_levels/` (005). The new TTS
abstraction lives beside the existing TTS provider in `services/tts/`, and is wired only in
`services/factory.py`. Frontend hooks shared across component folders go in `hooks/` (Principle V,
as 005's `useConversationLevels`). Colocated `*.test.tsx` files follow the existing convention and
are omitted from the tree.

### Suggested phase order (for `/speckit-tasks`)

1. **Foundation**, which blocks every story:
   - the `practice_languages` module and its invariants;
   - `VoiceInfo.language` and the German voices;
   - `run.sh`;
   - `voice_choices` with its seed and `AppSettingsRecord.voice_choices`;
   - `VoiceInstallation`, `SpeechForLanguage`, the factory wiring (`get_tts` kept until its callers
     move), and the shared `tests/support/fake_speech.py` double;
   - the 503 handler;
   - settings validation and the practice-languages endpoint;
   - conversation `*_name` fields;
   - the SC-005 preservation test, built from the frozen `schema_005.sql`.
2. **US1 (P1): German conversation, the MVP**:
   - `ConversationLanguages` at every prompt call site (names, not codes);
   - learning aids resolved from the conversation (R9: `learning.py`, and the helper by
     `conversation_id`), because German-aware tools are part of this story;
   - TTS by text language in chat, the audio endpoint **and flashcard word audio**, so the MVP
     never speaks a word in another language's voice (FR-018);
   - transcription language validation;
   - Settings `PracticeLanguageFieldset`, with the form's voice list following the language;
   - Home `PracticeLanguageNote`;
   - Chat `useConversationLanguage`, `ConversationLanguageTag` and `VoiceUnavailableNotice`, with
     transcription sending the conversation's code;
   - E2E.

   **Run both benchmarks here**, before anything else is built on the adherence and transcription
   assumptions. A hand-run `claude_live` German turn checks the Claude provider (FR-026).
3. **US2 (P1): switching without loss**:
   - the saved word's language from its source conversation (`vocabulary.py`);
   - Past Chats labels;
   - the cross-switch integration tests (FR-006, FR-009, FR-013, FR-014, FR-019; US2-2–US2-5);
   - the remembered Spanish voice (US2-4).
4. **US3 (P2): flashcards per language**:
   - columns and ORM fields;
   - storage keyword;
   - `AnalyticsService(language)`, and `SessionService` on the session's language;
   - router `?language=` and the 422;
   - LLM-cache names;
   - deleting `get_tts` once all three callers have moved;
   - frontend flashcards hooks and `AudioControls`;
   - E2E.
5. **US4 (P3): choosing a German voice**:
   - the Kerstin voice selectable in Settings;
   - the not-installed hint on `TtsVoiceField`;
   - E2E for "the next reply uses the chosen voice".
6. **Polish**:
   - `docs/architecture.md`: the language layer, and the "Open items" entries for the benchmark
     results and the ASCII-only search (R12);
   - `README.md`: the voice table and German setup;
   - `CLAUDE.md` Recent Changes;
   - the manual accessibility check;
   - quickstart validation.

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Seven React components stay over 20 lines while this feature modifies them: `Chat` (~480), `Home` (~270), `History` (~170), `Flashcards` (~315), `FlashcardDecks` (~295), `FlashcardAnalytics` (~160), `DeckConfigPanel` (~305) | Each change is one hook call or one self-loading element, with no new state, effects or handlers in the page:<br>• `Chat` swaps two settings-derived `useState`s for `useConversationLanguage`, and adds a header tag and a notice;<br>• `Home` adds `<PracticeLanguageNote />`;<br>• `History` renders one field per row;<br>• the three Flashcards pages replace an inline `useQuery` with a language-keyed hook, a net *reduction* in length;<br>• `DeckConfigPanel` adds `language` to the create payload from `usePracticeLanguages`. | Splitting these pages is the large frontend refactor that 004 and 005 already recorded as a follow-up (`useChatStream`, `useRecorderFlow` and the flashcard page splits). Doing it here would put E2E risk unrelated to languages into this diff, across seven screens. `AudioControls` (52 lines) *is* brought under the limit here, because its logic changes (function-length plan). |
| Three chat components stay over 20 lines while this feature modifies them: `MessageBubble` (~155), `LearningToolPanel` (~240) and `ExpressionHelperPanel` (~200). Added during implementation: the function-length plan above missed them | The change in each is a **removal**: the `targetLanguage`/`nativeLanguage` props and their pass-through go, because the server now takes every aid's language from the conversation (R9). `ExpressionHelperPanel` also renames two props and passes `conversationId` to `streamHelper`. No state, effect or handler is added | Same reasoning as the page components above: splitting them is the recorded frontend follow-up, and doing it here would put E2E risk unrelated to languages into this diff |
| `Settings` page body in `frontend/src/pages/Settings.tsx` stays at ~33 lines while this feature adds `<PracticeLanguageFieldset>` to it | The page is declarative composition only: one `useSettingsForm()` call and an ordered list of section components, with no logic, state or handlers. The change adds one element and passes `form.voicesForLanguage` instead of `form.voices`. This is the same shape, and the same justification, as 005's Complexity Tracking row for this page. | Nesting the layout in wrapper components to reach 20 lines would add indirection without separating any responsibility. The function-length rule exists to split *logic*, and there is none in the page. |
