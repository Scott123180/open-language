# Research: German Language Support

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Date**: 2026-09-26

Each entry records a decision, why it was made, and what else was considered. The spec had no
NEEDS CLARIFICATION markers. These entries settle the design questions that came up while reading
the code on `006-german-language-support` @ `3144321`.

The most important finding is that **a language is already a stored value almost everywhere**.
`conversations`, `vocabulary_items`, `word_llm_cache` and `app_settings` all carry a language code,
and every prompt builder already takes the language as a parameter. What is missing is:
1. a catalogue of which languages exist;
2. the places that read the *setting* where they should read the *conversation*;
3. TTS, which is not language-aware at all;
4. flashcard decks and sessions, which carry no language.

---

## R1. Language identity: ISO 639-1 codes, and the setting that already exists

**Decision**: A practice language is identified by its ISO 639-1 code: `es` and `de`. The learner's
practice language **is** the existing `app_settings.target_language` column. It is not a new
column. Codes are what is stored and sent over the wire; display names ("Spanish", "German") come
from the catalogue (R3).

**Rationale**:
- The live database holds `target_language = 'es'` and `native_language = 'en'` in `app_settings`,
  in all 38 conversations, and in all 27 vocabulary items. The ORM default is `"es"`. Codes are
  already the convention.
- faster-whisper's `language=` argument takes exactly these codes (R7), so the stored value doubles
  as the transcription hint with no mapping.
- `target_language` has been in the `PUT /api/settings` request since 001 but was never exposed in
  the UI or validated. Giving it a UI and a catalogue-derived pattern turns it into FR-001–FR-003
  without a schema change.

**Alternatives considered**:
- *A new `practice_language` column*: rejected. It would duplicate `target_language` and leave two
  sources of truth.
- *Storing names ("German")*: rejected. Names are presentation. Some Playwright fixtures use
  `'Spanish'`, but those are mocks; the backend has never stored a name.

---

## R2. Prompts receive language *names*, not codes

**Decision**: Every prompt receives the language's English name ("German", "Spanish", "English")
instead of its code. The code is turned into a name **once per request, at the router boundary**,
by a small value object, `ConversationLanguages.of(target_code, native_code)`. It is exported from
the new `practice_languages` module (R3). The prompt builders in `prompts/templates.py` and
`corrections/prompts.py` are **not edited**. Their parameters are already called `target_language`
and `native_language`, and now receive names.

**Rationale**:
- Today the stored codes are interpolated into prompts as they are. The roleplay prompt says "write
  EXCLUSIVELY in es… zero en words", and word info asks for "the es word 'casa'. Respond in en".
  `llama3.1:8b` copes with that for Spanish, but it is fragile.
- For German it would break. `de` is itself a common Spanish word ("of"). "Begin the conversation
  in de." is ambiguous to a model, and SC-002 requires 95% pure-German replies.
- There is a visible defect today: the corrections module's ask-to-repeat note
  (`build_repeat_request`) is shown to the learner and reads "Try to speak clearly in es." With
  names it reads "…in German."
- Converting at one boundary keeps the rule simple: **codes are storage identity, names are prompt
  text**. An unknown stored code raises `UnknownLanguage` rather than being guessed, the same
  choice 005 made for a corrupt level (`_level_of`).

**Consequences, accepted**:
- Spanish prompts change from `es` to `Spanish`. Live sessions rebuild once, because the standing
  prompt digest is part of the 004 session fingerprint, and the pool is in-memory anyway. Cached
  learning-tool results are keyed by message and content, not by prompt, so they stay valid. 005's
  Natural byte-identity property (`with_*_rules(p, NATURAL) == p`) is about the renderers and still
  holds.
- The corrections `TurnContext.target_language` and `native_language` fields now carry names.
  They are only used to build prompt text, and their docstring will say so.

**Alternatives considered**:
- *Keep codes*: rejected for the reasons above.
- *Convert inside each template function*: rejected. It would edit two prompt modules that 003 and
  005 deliberately left stable, and make every template depend on the catalogue.
- *A new "German context" sentence in the roleplay prompt* ("set the scene in a German-speaking
  place"): not needed. The language rule already makes the partner speak German, and the scenarios
  are country-neutral (R11). It can be added later in the catalogue if the benchmark (R8) shows a
  need.

---

## R3. One catalogue: the `practice_languages` domain module (FR-005)

**Decision**: A new domain module, `backend/app/practice_languages/`, patterned on
`conversation_levels/`. It owns no tables and no router. Its public interface, exported from the
package root only:

| Name | What it is |
|---|---|
| `PracticeLanguage` | Frozen value object: `code`, `name`, `default_voice` |
| `PRACTICE_LANGUAGES` | Ordered mapping `code → PracticeLanguage`: `es` (Spanish), `de` (German) |
| `DEFAULT_PRACTICE_LANGUAGE` | `"es"` (FR-001) |
| `UnknownLanguage` | `ValueError` subclass for a code outside the catalogue |
| `language_name(code)` | English name of a practice *or* native language (`en` → "English") |
| `ConversationLanguages` | The pair a conversation uses, as prompt names (R2) |
| `voice_for(code, voice_choices)` | The learner's voice for a language, or its default (R5) |
| `voice_unavailable_message(code)` | The plain-language FR-018 message |

Voices stay in `services/tts/voices.py`, which is the TTS catalogue. Each `VoiceInfo` gains a
`language` property derived from its locale (`de_DE` → `de`).

**Rationale**:
- FR-005: adding French later means one `PracticeLanguage` entry, its `VoiceInfo` entries, and its
  voice keys in `run.sh`. No feature code changes. Invariant tests tie these together:
  - every language has at least one voice;
  - every default voice belongs to its own language;
  - every catalogue voice is in `run.sh`'s download list.
- The same shape as `conversation_levels` keeps the codebase consistent, and satisfies Principle V:
  routers import only the package root.
- Voices remain TTS data (Piper model keys), so the language catalogue references a voice key but
  never a TTS class (Principle VI).

**Alternatives considered**:
- *Put the catalogue in `config.py`*: rejected. It is domain data with invariants, not deployment
  configuration.
- *Language list only on the frontend*: rejected. The backend validates settings and builds prompts,
  so it must own the list. The frontend reads it from a new endpoint (contracts §1).
- *Use `Intl.DisplayNames` on the frontend for names*: rejected as the source of truth. It would
  work, but it would be a second list that can drift from the backend's. Names reach the frontend
  from the catalogue endpoint and from conversation responses instead (contracts §1, §4).

---

## R4. The German voices

**Decision**: Add two Piper voices, both verified in the upstream `rhasspy/piper-voices` index
(`voices.json`, fetched 2026-09-26):

| Key | Speaker | Quality | Size | Role |
|---|---|---|---|---|
| `de_DE-thorsten-medium` | male, Germany | medium | 63 MB | **Default** (mirrors `es_ES-davefx-medium`) |
| `de_DE-kerstin-low` | female, Germany | low | 63 MB | Alternative (mirrors Spanish's male/female pair) |

Both are added to `run.sh`'s `PIPER_VOICES`, so `./run.sh --setup` fetches them once. After that,
all German speech runs offline (FR-017, SC-007).

**Rationale**:
- Thorsten is the best-known open German voice, and medium quality is the same tier as the Spanish
  default, so latency is comparable.
- No single-speaker female German voice exists above "low" quality. `kerstin-low` is the clearest
  of the low-tier options (`ramona`, `eva_k` x-low), and it gives learners the same choice of voice
  gender that Spanish offers.

**Alternatives considered**:
- `de_DE-thorsten-high` (114 MB): rejected as the default. It is slower to synthesise on CPU for a
  small gain; it could be added later as a catalogue entry.
- `de_DE-mls-medium`, `de_DE-thorsten_emotional-medium`: rejected. They are multi-speaker models,
  and `PiperTTSProvider` does not pass a speaker id.
- `de_DE-eva_k-x_low`: rejected. Its quality is audibly poor for listening practice.

---

## R5. Remembering a voice per language (FR-016)

**Decision**:
- A new table, `voice_choices` (`target_language` primary key, `voice_key`, `updated_at`), holds
  only the voices the learner has explicitly chosen.
- `voice_for(code, choices)` returns the chosen voice **if it belongs to that language**, and the
  language's `default_voice` otherwise.
- The existing `app_settings.tts_voice` column becomes legacy. It is read exactly once, by an
  idempotent seed in `_migrate_db()`: if the legacy voice belongs to the stored `target_language`,
  the seed does `INSERT OR IGNORE` of that pair.
- `AppSettingsRecord.tts_voice` is replaced by `voice_choices: Mapping[str, str]`.

**Rationale**:
- FR-024 and US2-4: a learner who picked "Daniela (Argentina)" before upgrading must still have her
  afterwards. Before 006 the target language could only be `es`, so the seed carries the choice
  across exactly.
- The resolver's language check is the FR-018 safety net. A stale or mismatched stored choice can
  never make German text use a Spanish voice, whatever is in the table.
- A table keyed by language is the relational form of "one voice per language". A third language
  needs no schema change.

**Alternatives considered**:
- *A `tts_voice_de` column*: rejected. It violates FR-005 and needs a column per language.
- *A JSON column on `app_settings`*: rejected. It is harder to update atomically, cannot be
  constrained, and needs the same seed step.
- *Keep writing `tts_voice` as "the current language's voice"*: rejected. It would be two sources of
  truth that must be kept in sync on every language switch.
- *Read-through fallback to the legacy column forever*: rejected. It would keep a dead column in
  live logic permanently. The one-time seed confines it to the migration.

---

## R6. Speaking in the right voice, and never in the wrong one (FR-014, FR-018)

**Decision**: Voice selection follows the language of **the text being spoken**, never the current
setting:
- chat replies and `GET /audio/tts/{message_id}` use the message's conversation language;
- `GET /flashcards/tts/{id}` uses the word's own `target_language`.

The pieces:
- `services/tts/base.py` gains a `VoiceInstallation` ABC (`is_installed(voice_key) -> bool`) and
  `VoiceUnavailable(TTSError)`, which carries a `user_message`.
- `services/tts/piper.py` gains `PiperVoiceInstallation(voice_dir)`: a voice is installed when both
  its `.onnx` and `.onnx.json` files exist.
- `services/tts/selection.py` gains `SpeechForLanguage`. It is built only in `services/factory.py`,
  which injects the voice resolver (`voice_for` bound to the learner's choices), the installation
  check and the Piper builder. `provider_for(code)` returns a `TTSProvider` or raises
  `VoiceUnavailable`.
- `main.py` maps `VoiceUnavailable` to **503** with the plain message, like the existing `LLMError`
  handler.
- The chat's background synthesis (`_schedule_tts`) checks installation first and skips synthesis
  instead of failing silently in the executor.

What the learner sees:
- **Chat**: the practice-languages endpoint reports `is_voice_installed` per language (contracts
  §1). The Chat page shows one persistent notice for the conversation's language and does not
  auto-play.
- **Flashcards**: `AudioControls` reads the 503 `detail` when playback fails and shows it.

**Rationale**:
- Principle VI: routers depend on the `SpeechForLanguage` abstraction, and only the factory names
  Piper. A missing voice is reported, not replaced ("no silent fallback").
- Principle IV: the message says what happened and what to do: "The German voice isn't installed,
  so replies can't be read aloud. Run `./run.sh --setup` to download it. You can keep practising in
  text."
- Today `TTSError` escapes as a 500 from the audio endpoint, and is lost entirely in the chat
  background task. Both are fixed on the way.

**Alternatives considered**:
- *Fall back to the default voice of another language*: forbidden by FR-018.
- *Detect failure only from the `<audio>` element*: rejected for chat. Every reply would fail
  separately; one up-front notice is clearer.

---

## R7. Transcribing German (FR-013, SC-003)

**Decision**: No model change. The Whisper models the app already uses (`base`, `small`, `medium`)
are multilingual.
- The Chat page sends **the conversation's** `target_language` as the `language` hint. Today it
  sends the setting's, which breaks FR-009 for an older conversation.
- The backend validates the hint against the practice-language catalogue: **422** for an unknown
  code.
- Forcing the hint means Spanish speech in a German conversation is transcribed as German rather
  than silently switching language (spec Edge Cases).

**Rationale**:
- faster-whisper accepts `language="de"`. With a forced language the model uses German tokens, so
  ä, ö, ü and ß come out as characters and are not transliterated. The text is UTF-8 end to end
  (SQLite TEXT, JSON, React), with no normalisation step anywhere (R12).
- Accuracy risk: Whisper `base` has a somewhat higher word-error rate on German than on Spanish.
  SC-003 is measured by a hand-run benchmark (R14). The existing Whisper-model setting (`small`,
  `medium`) is the documented remedy if `base` falls short. It is the same lever Spanish learners
  already have.

**Alternatives considered**:
- *Auto-detect the language (no hint)*: rejected. It violates the edge case and FR-013.
- *Pass `conversation_id` and derive the language server-side*: considered. It is more robust, but
  it couples a generic transcription endpoint to conversations. The client already holds the
  conversation, and the value is validated. This could be revisited if another caller appears.

---

## R8. German on the language-model providers (FR-026, SC-002)

**Decision**: No provider change. Both providers receive the same prompts with "German" in place
of "Spanish".
- `llama3.1` lists German among its eight officially supported languages, alongside English and
  Spanish.
- Claude is fluent in German.

SC-002 is measured by a hand-run `@benchmark` test modelled on 005's harness:
- 10 scenarios × 5 scripted German learner turns, against the default local model;
- each reply is checked for non-German words with `wordfreq` (already a dev dependency, 3.1.1). A
  token is flagged when it is rare in German (Zipf < 2.0) but common in English or Spanish
  (Zipf ≥ 3.0), after excluding proper nouns and a short allow-list of loanwords
  (Hotel, Taxi, Ticket, OK);
- flagged replies go to a review sheet for a human verdict, as in 005.

**Refined during implementation (T067)**: the "rare in German (Zipf < 2.0)" test cannot flag the
words SC-002 is about, because wordfreq's German list carries common English loans ("the" is 5.6,
"quiero" 2.4). The benchmark instead flags a token when it is common in English or Spanish
(Zipf ≥ 3.0) **and** at least 1.5 Zipf more frequent there than in German. On the top 5,000 German
tokens, every word this flags is an English, Spanish or French function word. See
`backend/tests/integration/practice_languages/text_purity.py`.

**Rationale**: The same measure-then-decide path 003 and 005 used. If `llama3.1:8b` falls short, the
spec's "Quality limits carry over" assumption applies, and the result is recorded in
`docs/architecture.md` § "Open items". No new dependency is needed.

**Alternatives considered**:
- *`lingua-language-detector` for sentence-level language ID*: rejected. It is a new dependency, and
  sentence-level ID misses the single English word SC-002 is about.
- *An LLM judge*: rejected. It is circular (the same model grading itself) and not reproducible.

---

## R9. Learning aids follow the conversation, derived server-side (FR-009)

**Decision**: Every learning aid resolves its languages **on the server** from the conversation it
belongs to. The client-supplied language fields are removed from the request models:

| Endpoint | Today | After |
|---|---|---|
| `POST /learning/phrasing` | `app_settings.target_language` (**the setting**: an FR-009 bug) | message → conversation |
| `POST /learning/word-lookup` | client `target_language`, `native_language` | message → conversation |
| `POST /learning/translate` | client `native_language` | message → conversation |
| `POST /learning/grammar` | `app_settings.native_language` | message → conversation |
| `POST /chat/helper` | client `target_language`, `native_language` | new `conversation_id` → conversation |
| `POST /chat/{id}/suggestions` | conversation | unchanged |
| Roleplay open, message, warm | conversation | unchanged, now as names (R2) |
| `POST /vocabulary` | `app_settings.target_language` | source conversation, falling back to the practice language when none is given (FR-019) |

A shared helper, `conversation_languages_for_message(storage, message_id)`, returns a
`ConversationLanguages`, or raises 404 when the message does not exist.

**Rationale**:
- The spec's FR-009 scenario (continuing an old Spanish chat while German is selected) is exactly
  where client-held state goes wrong. `Chat.tsx` loads the languages from **settings** today.
- Every learning request already carries `message_id`, so the server can always find the
  conversation.
- Pydantic ignores unknown fields by default, so an old client that still sends the removed fields
  keeps working.

**Alternatives considered**:
- *Keep client-supplied fields and fix `Chat.tsx`*: rejected. It is correct only as long as every
  caller is correct, and the phrasing endpoint ignores the field anyway.

---

## R10. Flashcards per language (FR-020 – FR-023, SC-006)

**Decisions**:
1. **Two additive columns**: `decks.target_language` and `practice_sessions.target_language`, both
   `VARCHAR(20) NOT NULL DEFAULT 'es'`. The default *is* FR-021's "existing decks and practice
   history belong to Spanish", applied by SQLite to existing rows at `ALTER TABLE` time.
   - A session copies its deck's language when it starts, because `practice_sessions.deck_id`
     becomes NULL when a deck is deleted and the history must keep its language.
   - Card results, rating history and classification snapshots get their language by joining to
     the session or word. They need no column.
   - The ORM columns have **no Python default**, so a new row without a language fails loudly
     instead of silently becoming Spanish.
2. **The language is explicit on every collection endpoint**:
   - `GET /flashcards/words`, `GET /flashcards/decks` and `GET /flashcards/analytics` take a
     required `language` query parameter;
   - `POST /flashcards/decks` takes it in the body.

   All four validate it against the catalogue.
3. **By-id endpoints stay unscoped.** A session, deck or word is fetched by id, and a session-bound
   request (record card, end, summary, missed deck) uses **the session's own language** for its
   classification snapshot and streak. That is the "session in progress finishes in its own
   language" edge case.
4. **Storage methods take a required `language` keyword** where they list or count: `list_words`,
   `list_decks`, `create_deck`, `create_session`, `get_sessions_since`, `get_card_results_since`,
   `get_classification_counts` and `get_classification_snapshots_since`. `AnalyticsService` is
   constructed with a language. `SessionService` reads the session's language.

**Rationale**:
- *Explicit parameter over reading the setting on the server*: the flashcards module then needs no
  dependency on app settings. More importantly, the frontend's TanStack Query keys include the
  language. With a server-resolved language the key would stay `['flashcard-words']` after a
  switch, and the stale Spanish list would flash on screen before the refetch. That is an SC-006
  violation.
- *Required, not defaulted*: every caller is forced to decide. A forgotten language is a 422 in
  tests, not a silent Spanish view.
- `vocabulary_items` already has `UNIQUE(word, target_language)`, and `word_llm_cache` is already
  keyed by language. FR-023 ("same spelling, two languages, two words") holds today and gets a
  regression test.
- `POST /flashcards/decks` with `selected_word_ids` from another language returns **422** ("Some
  selected words are in another language. Reload the word list."). It does not silently drop them.

**Alternatives considered**:
- *A language-scoped storage instance* (`storage.scoped_to("de")`): elegant, but it is ambient
  context, which Principle V asks to avoid. It also makes the in-progress-session edge case easy to
  get wrong, because the scope would come from the request rather than the session.
- *A combined cross-language view*: out of scope per the spec's Assumptions.

---

## R11. Scenarios need no German versions

**Decision**: No change to `services/scenario/`. All ten scenarios ("Buy a Train Ticket", "Order at
a Restaurant", …) are country-neutral in title, description and `ai_context_prompt`. The unused
`Scenario.target_language_hint` field stays unused.

**Rationale**: FR-007 is met because the standing prompt already carries the conversation's
language. Checked with `grep` for Spain, Mexico, peso and euro in `scenario/static.py`: no hits.

---

## R12. German text: umlauts, ß and capitalisation

**Decision**: No normalisation is added. Regression tests pin the existing behaviour.
- Word selection in `MessageBubble` takes the browser selection verbatim. Vocabulary is stored
  exactly as sent, and uniqueness is by exact `(word, target_language)`. So "Haus" stays "Haus",
  and "Straße" stays "Straße".
- The corrections prompt already says "Never report… capitalisation", and "a word or construction
  that is valid in some region where {target_language} is spoken". With the name substituted, this
  covers Austrian and Swiss German with no edit (spec Edge Cases).

**Known limitation (not a regression)**: the word-list `search` filter uses SQLite `ILIKE`, which
folds only ASCII case, so "über" does not find "Über". Spanish has the same gap today ("é" vs
"É"), so it is recorded in `docs/architecture.md` § "Open items" and not fixed here.

---

## R13. Upgrade and preservation (FR-024, FR-025, SC-005)

**Decision**: The upgrade is entirely additive:
- two `_ADDITIVE_COLUMNS` entries (R10);
- one new table via `create_all()` (R5);
- one idempotent seed (R5).

No existing row is updated. An integration test builds a pre-006 database (the 005 schema, with
Spanish conversations, words, decks, sessions and a non-default voice), runs `init_db()` twice, and
asserts:
- every row is byte-identical;
- decks and sessions read back as `es`;
- the Spanish voice is preserved;
- the practice language is `es`.

**Rationale**: This matches the project's storage convention ("Schema changes are additive… There
is no migration framework"). Running `init_db()` twice proves idempotence.

---

## R14. Measuring the success criteria that need a real model

| SC | How | Where |
|---|---|---|
| SC-001 (< 30 s to a German chat) | Timed manual run | quickstart §4 |
| SC-002 (≥ 95% pure German) | `@benchmark` harness (R8), hand-run | `tests/integration/practice_languages/test_german_benchmark.py` |
| SC-003 (≥ 90% of 20 sentences transcribed) | `@benchmark`: 20 fixed German sentences, each containing umlauts or ß. They are synthesised with the *non-default* German voice (`kerstin`) so the check does not grade Whisper on the voice the app itself speaks, then transcribed with the configured Whisper model. A pass requires every umlaut or ß word to be spelled exactly, and word error rate ≤ 20% after case and punctuation are normalised. A second, manual run with the learner's own voice is in quickstart §5. | `…/test_transcription_benchmark.py` |
| SC-004 (feature parity) | The Spanish feature checklist from quickstart §4, run in German | quickstart §4 |
| SC-005 (preservation) | Automated (R13) | integration |
| SC-006 (no cross-language leakage) | Automated: storage, router and E2E tests with mixed-language fixtures | integration + E2E |
| SC-007 (offline) | Manual: disconnect the network with the local defaults | quickstart §5 |

The `benchmark` marker is already deselected by `addopts`, so these are never skipped: they are
simply not collected by default. This is the established 003/005 pattern.

---

## R15. Frontend shape

**Decisions**:
- **`hooks/usePracticeLanguages.ts`** (new) loads `GET /settings/practice-languages`. It is shared
  by Settings, Home and Flashcards, so no `components/` folder imports another (Principle V, as
  005's `useConversationLevels`).
- **Settings**: a `PracticeLanguageFieldset` radio group placed before the voice field.
  - Changing the language swaps the voice list to that language's voices and pre-selects that
    language's remembered voice (`selected_voice` from the catalogue response).
  - One Save persists both. There is no immediate save: unlike the chat header's level control,
    this is a form.
- **Home**: a self-loading `PracticeLanguageNote` ("Practising **German** · Change in Settings")
  meets FR-004 with one element added to `Home`.
- **Chat**:
  - a `useConversationLanguage(conversation)` hook replaces the two settings-derived `useState`s. It
    supplies the names for the helper label (FR-011) and the code for transcription (R7);
  - a `ConversationLanguageTag` in the header shows the language with no control (spec Edge
    Cases);
  - a `VoiceUnavailableNotice` covers FR-018;
  - `MessageBubble` and `LearningToolPanel` lose their language props, because the server derives
    the languages (R9).
- **Past Chats**: each row shows `target_language_name` from the conversation response.
- **Flashcards**: `hooks/flashcards/` query hooks (`useWordLibrary`, `useDecks`,
  `useFlashcardAnalytics`) put the practice language in both the request and the query key (R10).
  The four pages call a hook instead of an inline `useQuery`, which shortens them.

**Rationale**: Every change is a hook or a self-contained component, so the long page components
(Complexity Tracking) gain no state, effects or handlers.
