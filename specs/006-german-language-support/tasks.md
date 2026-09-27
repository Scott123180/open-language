---

description: "Task list for 006 — German Language Support"
---

# Tasks: German Language Support

**Input**: Design documents from `/specs/006-german-language-support/`
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/api.md](contracts/api.md), [quickstart.md](quickstart.md)

**Tests**: Test tasks are MANDATORY per the TDD constitution (Principle III). Every test task is
written first and must be seen to FAIL before the implementation task that follows it. The tests
are at the level each guarantee in [contracts/api.md](contracts/api.md) names: unit, contract,
integration, Vitest and Playwright.

**Organization**: Tasks are grouped by user story, so each story can be implemented and tested on
its own:
- **Foundational** builds the catalogue, voice storage, the TTS abstraction and the settings API.
- **US1** makes a German conversation work end to end: prompts, speech, Settings, Home and Chat.
- **US2** proves nothing is lost across a switch.
- **US3** scopes flashcards by language.
- **US4** is voice choice.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1–US4 (the spec.md user stories); absent in Setup, Foundational and Polish
- Paths are relative to the repository root (`backend/app`, `backend/tests`, `frontend/src`,
  `frontend/e2e`)

## Standing rules for every task

- **Python** runs through the venv only: `backend/.venv/bin/pytest`, `backend/.venv/bin/ruff` and
  `backend/.venv/bin/black`, run from `backend/`.
- **Function length**: every new or modified function is ≤ 20 lines (Constitution I). The only
  permitted exceptions are the React components in plan.md § Complexity Tracking: the seven
  page components, and the `Settings` layout.
- **Existing functions over 20 lines** listed in plan.md § "Function-length plan" are brought under
  the limit in the same task that modifies them.
- **Imports**: code outside the module imports only from the package root `app.practice_languages`
  (Principle V). Only `backend/app/services/factory.py` may import `PiperTTSProvider` or
  `PiperVoiceInstallation` (Principle VI).
- **Files not modified**:
  - `backend/app/prompts/templates.py`
  - `backend/app/corrections/prompts.py`
  - anything under `backend/app/services/llm/`, `backend/app/services/conversation/`,
    `backend/app/services/stt/`, `backend/app/services/scenario/` and
    `backend/app/conversation_levels/`

  (plan.md § Project Structure)
- **Language literals**: no code outside `backend/app/practice_languages/catalog.py`,
  `backend/app/services/tts/voices.py` and test fixtures branches on, or hardcodes, the codes `"es"`
  or `"de"`. Defaults come from `DEFAULT_PRACTICE_LANGUAGE`.
- **Frontend styling** uses design-system tokens only (`docs/design-system.md`):
  - no hex colours;
  - navigation and tag text uses `--color-text` or `--color-text-muted`;
  - cards use `--radius-lg`;
  - shadows use `--shadow-*`.
- **Frontend completion**: a frontend task is complete only when `cd frontend && npm run test:e2e`
  passes.

---

## Phase 1: Setup

**Purpose**: Package skeletons and a green baseline to measure against.

- [X] T001 [P] Create empty package files `backend/app/practice_languages/__init__.py`, `backend/tests/unit/practice_languages/__init__.py` and `backend/tests/integration/practice_languages/__init__.py`
- [X] T002 Record the green baseline before any change:
  - from `backend/`: `backend/.venv/bin/pytest`, `backend/.venv/bin/ruff check .` and `backend/.venv/bin/black --check .`;
  - from `frontend/`: `npm run lint`, `npm run build` (runs `tsc -b`, the only step that type-checks test files), `npm test` and `npm run test:e2e`.

  All must pass. Note any pre-existing failure in the PR description rather than fixing it in this feature.
- [X] T003 Back up the local database: `cp ~/.open-language/app.db ~/.open-language/app.db.pre-006`. It is used by quickstart §4 (SC-005) and must be taken before the app runs any 006 code.
- [X] T004 Freeze the pre-006 schema as a test fixture, `backend/tests/fixtures/schema_005.sql` (analysis U2). The SC-005 tests must not build their "before" database from the live ORM metadata, which already contains 006 tables and columns.
  - `git worktree add "$SCRATCH/wt-005" 329cf72` (the 005 release commit).
  - In that worktree, run `init_db()` against an empty database with `OPEN_LANGUAGE_DB_PATH` set to a scratch file, using this repository's `backend/.venv/bin/python`.
  - Dump `sqlite3 <file> .schema > backend/tests/fixtures/schema_005.sql`, then `git worktree remove "$SCRATCH/wt-005"`.
  - Check the dump: it contains `CREATE TABLE decks` and `CREATE TABLE practice_sessions` **without** `target_language`, and no `voice_choices` table. Commit it with a header comment naming the source commit.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**:
- the `practice_languages` catalogue;
- German voices in the TTS catalogue and `run.sh`;
- per-language voice storage and its seed;
- the `SpeechForLanguage` abstraction;
- the validated settings API with the practice-languages endpoint;
- conversation name fields;
- the frontend API types, shared hook and fixtures.

Every story depends on these.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Tests for the foundation (write first, see them fail)

- [X] T005 [P] Write catalogue unit tests in `backend/tests/unit/practice_languages/test_catalog.py` (data-model §1, invariants I1–I6):
  - `PRACTICE_LANGUAGES` keys iterate exactly `["es", "de"]`;
  - names are "Spanish" and "German";
  - the default voices are `es_ES-davefx-medium` and `de_DE-thorsten-medium`;
  - `DEFAULT_PRACTICE_LANGUAGE == "es"` and is in the catalogue (I1);
  - every language has ≥ 1 voice in `AVAILABLE_VOICES` with a matching `.language` (I2);
  - every `default_voice` exists in `AVAILABLE_VOICES` and belongs to its own language (I3);
  - every `AVAILABLE_VOICES` key appears in the `PIPER_VOICES=( … )` array of the repository's `run.sh`, parsed with a regex over the file text (I4);
  - no code is in both `PRACTICE_LANGUAGES` and `NATIVE_LANGUAGE_NAMES` (I5);
  - every code matches `^[a-z]{2}$` (I6);
  - `PracticeLanguage` is frozen: assigning a field raises `FrozenInstanceError`;
  - `set(app.practice_languages.__all__)` is exactly `{"PracticeLanguage", "PRACTICE_LANGUAGES", "DEFAULT_PRACTICE_LANGUAGE", "UnknownLanguage", "language_name", "ConversationLanguages", "voice_for", "voice_unavailable_message"}`.
- [X] T006 [P] Write naming unit tests in `backend/tests/unit/practice_languages/test_naming.py` (data-model §2, research R2):
  - `language_name("de") == "German"`, `language_name("es") == "Spanish"` and `language_name("en") == "English"`;
  - `language_name("fr")` and `language_name("")` raise `UnknownLanguage`, a `ValueError` subclass whose message names the code;
  - `ConversationLanguages.of("de", "en")` has `target_code == "de"`, `target_name == "German"` and `native_name == "English"`;
  - `ConversationLanguages.of("xx", "en")` and `ConversationLanguages.of("de", "xx")` raise `UnknownLanguage`;
  - the value object is frozen.
- [X] T007 [P] Write voice-resolution unit tests in `backend/tests/unit/practice_languages/test_voices.py` (data-model §4):
  - `voice_for("de", {})` is `"de_DE-thorsten-medium"`;
  - `voice_for("de", {"de": "de_DE-kerstin-low"})` is `"de_DE-kerstin-low"`;
  - `voice_for("de", {"de": "es_ES-davefx-medium"})` is `"de_DE-thorsten-medium"`, because a mismatched choice is never returned (FR-018);
  - `voice_for("de", {"de": "xx_XX-gone-low"})` is `"de_DE-thorsten-medium"`;
  - `voice_for("es", {"de": "de_DE-kerstin-low"})` is `"es_ES-davefx-medium"`;
  - `voice_for("fr", {})` raises `UnknownLanguage`;
  - `voice_unavailable_message("de")` contains "German voice isn't installed", "./run.sh --setup" and "keep practising in text", and contains no voice key.
- [X] T008 [P] Extend `backend/tests/unit/services/test_voices.py` (data-model §3):
  - `AVAILABLE_VOICES` has four entries in the order `es_ES-davefx-medium`, `es_AR-daniela-high`, `de_DE-thorsten-medium`, `de_DE-kerstin-low`;
  - `de_DE-thorsten-medium` is display name "Thorsten (Germany)", male, locale `de_DE`, quality medium, speaking rate natural;
  - `de_DE-kerstin-low` is "Kerstin (Germany)", female, `de_DE`, low, natural;
  - `VoiceInfo(… locale="de_DE" …).language == "de"`;
  - `voices_for("de")` returns the two German voices in catalogue order;
  - `voices_for("fr") == ()`;
  - keep the existing `test_davefx_is_the_first_voice`.
- [X] T009 [P] Write `backend/tests/unit/services/test_speech_selection.py` for `SpeechForLanguage` (contracts §9, research R6), using a fake `VoiceInstallation` and a recording builder:
  - `voice_key("de")` returns what the injected resolver returns;
  - `is_available("de")` is the installation's answer for that key;
  - `provider_for("de")` calls the builder once with that key and returns its provider;
  - when the voice is not installed, `provider_for` raises `VoiceUnavailable` whose `user_message` equals the injected message function's output for `"de"`, and **the builder is never called** (no fallback);
  - `VoiceUnavailable` is a subclass of `TTSError`.
- [X] T010 [P] Extend `backend/tests/unit/services/test_piper_tts.py`: `PiperVoiceInstallation(tmp_path).is_installed(key)` is `True` only when both `<key>.onnx` and `<key>.onnx.json` exist in `tmp_path`; it is `False` with either file missing, and `False` for an empty directory.
- [X] T011 [P] Extend `backend/tests/unit/test_database.py` (data-model §4 seed):
  - after `init_db()` the `voice_choices` table exists, with columns `target_language` (primary key), `voice_key` and `updated_at`;
  - an `app_settings` row `('es', 'es_AR-daniela-high')` is seeded as a `voice_choices` row `('es', 'es_AR-daniela-high')`;
  - a row `('de', 'es_ES-davefx-medium')` (mismatched) seeds nothing;
  - an existing `voice_choices` row is not overwritten by the seed;
  - with no `app_settings` row, nothing is seeded and nothing fails;
  - running `_migrate_db()` twice leaves exactly one row (idempotent).
- [X] T012 [P] Extend `backend/tests/unit/services/test_sqlite_storage.py` (data-model §6):
  - `get_settings().voice_choices == {}` on a fresh database;
  - after `save_voice_choice("de", "de_DE-kerstin-low")` it is `{"de": "de_DE-kerstin-low"}`;
  - a second `save_voice_choice("de", "de_DE-thorsten-medium")` updates in place, so there is still one row for `de`;
  - saving for `de` leaves an `es` choice untouched;
  - `AppSettingsRecord` has no `tts_voice` attribute.

  Update the `AppSettingsRecord(...)` constructions in `backend/tests/unit/services/test_factory.py` and `backend/tests/unit/services/llm/test_selection.py` to drop `tts_voice=` (a compile-level change to test fixtures, done here so the suite is red only for the new behaviour).
- [X] T013 [P] Extend `backend/tests/contract/service_interfaces/test_storage_provider.py`: `StorageProvider` declares the abstract method `save_voice_choice(target_language, voice_key)`, and `SQLiteStorageProvider` implements it.
- [X] T014 [P] Extend `backend/tests/contract/service_interfaces/test_tts_provider.py`: `VoiceInstallation` is an ABC with exactly one abstract method, `is_installed`, and `PiperVoiceInstallation` implements it.
- [X] T015 [P] Write the endpoint contract test in `backend/tests/contract/test_practice_languages_api.py` (contracts §1). Override `get_voice_installation` with a fake.
  - `GET /api/settings/practice-languages` returns 200 with exactly the `PRACTICE_LANGUAGES` entries, in order.
  - Each item's keys are exactly `{"language_id", "display_name", "is_default", "default_voice", "selected_voice", "is_voice_installed", "voice_unavailable_message"}`.
  - Exactly one item has `is_default: true`, and it is `DEFAULT_PRACTICE_LANGUAGE`.
  - The set of `language_id` values equals the set `PUT /api/settings` accepts for `target_language`: PUT each id and expect 200.
  - `voice_unavailable_message` is non-null exactly when `is_voice_installed` is false (fake German uninstalled, Spanish installed).
  - `selected_voice` for `de` is the default when the stored choice is the mismatched `es_ES-davefx-medium`.
- [X] T016 [P] Extend `backend/tests/integration/routers/test_settings.py` (contracts §2, §3), one test per row of the contracts §2 table:
  - `PUT {"target_language": "de"}` → 200, and the response `tts_voice` is `de_DE-thorsten-medium`; the stored `es` choice is unchanged;
  - `PUT {"target_language": "de", "tts_voice": "de_DE-kerstin-low"}` → 200, remembered for `de`;
  - `PUT {"tts_voice": "de_DE-kerstin-low"}` with stored `es` → 422 with detail "That voice is for German. Choose a Spanish voice.", and nothing written;
  - `PUT {"tts_voice": "xx_XX-nope-low"}` → 422 "Unknown voice.";
  - `PUT {"target_language": "fr"}` → 422;
  - switching `de` → `es` returns the earlier Spanish choice (US2-4);
  - a combined language and LLM change applies both, and the provider is unchanged by the language (FR-026);
  - `GET /api/settings/voices` returns four voices, each with `language` and `is_installed` (fake installation).

  Replace any existing assertion that `PUT {"tts_voice": …}` is stored unvalidated.
- [X] T017 [P] Write `backend/tests/integration/practice_languages/test_upgrade_preserves_data.py` (SC-005, FR-024, research R13):
  - Build a pre-006 SQLite file in `tmp_path` by executing `backend/tests/fixtures/schema_005.sql` (T004) with `sqlite3.Connection.executescript`. Never use `create_all()` here: the shared `Base.metadata` already holds the 006 schema, so a database built from it cannot fail this test for the right reason.
  - Seed it with: two Spanish conversations with messages, three Spanish vocabulary items, and `app_settings` with `target_language='es'` and `tts_voice='es_AR-daniela-high'`.
  - Snapshot every row of `conversations`, `messages`, `vocabulary_items` and `app_settings` (pre-006 columns only).
  - Run `init_db()` **twice** against that file, by pointing `OPEN_LANGUAGE_DB_PATH` at it and rebuilding the engine the way `tests/integration/conftest.py` does.
  - Assert:
    - every snapshotted row is identical;
    - `GET /api/settings` shows `target_language == "es"` and `tts_voice == "es_AR-daniela-high"`;
    - there is exactly one `voice_choices` row.

  US3 extends this test to decks and sessions (T077).
- [X] T018 [P] Extend `backend/tests/integration/routers/test_conversations.py` (contracts §4):
  - every `ConversationResponse` (create, get, list, patch) carries `target_language_name` and `native_language_name`;
  - a conversation created while the stored `target_language` is `de` has `target_language == "de"`, `target_language_name == "German"` and `native_language_name == "English"`;
  - a mixed es/de fixture lists each conversation with its own name.
- [X] T019 [P] Write `backend/tests/integration/test_voice_unavailable_surface.py` (research R6), modelled on `backend/tests/integration/test_llm_error_surface.py`: a route raising `VoiceUnavailable("…message…")` returns **503** with `{"detail": "…message…"}`, not a 500.

### Implementation for the foundation

- [X] T020 Implement `backend/app/practice_languages/catalog.py` to pass T005's catalogue assertions:
  - `@dataclass(frozen=True, slots=True) class PracticeLanguage` with `code: str`, `name: str` and `default_voice: str`;
  - `PRACTICE_LANGUAGES: Mapping[str, PracticeLanguage]` as a `MappingProxyType` holding `es` ("Spanish", `es_ES-davefx-medium`) then `de` ("German", `de_DE-thorsten-medium`);
  - `DEFAULT_PRACTICE_LANGUAGE = "es"`;
  - `NATIVE_LANGUAGE_NAMES: Mapping[str, str] = MappingProxyType({"en": "English"})`.
- [X] T021 Implement `backend/app/practice_languages/naming.py` to pass T006:
  - `class UnknownLanguage(ValueError)`, whose message names the code and says it is not in the language catalogue;
  - `language_name(code: str) -> str`, looking in `PRACTICE_LANGUAGES`, then in `NATIVE_LANGUAGE_NAMES`;
  - `@dataclass(frozen=True, slots=True) class ConversationLanguages` with `target_code`, `target_name` and `native_name`, and `@classmethod of(cls, target_code, native_code)`. The target must be a practice language; `language_name` is used for both.
- [X] T022 Add a read-only `language` property to `VoiceInfo` (`self.locale.split("_")[0]`), the two German `VoiceInfo` entries exactly as in data-model §3, and `voices_for(language_code: str) -> tuple[VoiceInfo, ...]`, all in `backend/app/services/tts/voices.py` (passes T008).
- [X] T023 Implement `backend/app/practice_languages/voices.py` to pass T007. It imports `AVAILABLE_VOICES` from `app.services.tts.voices`, which is catalogue data, not a provider.
  - `voice_for(code: str, voice_choices: Mapping[str, str]) -> str` returns the choice only if it is a known voice whose `language == code`, and otherwise `PRACTICE_LANGUAGES[code].default_voice`. It raises `UnknownLanguage` for an unknown code.
  - `voice_unavailable_message(code: str) -> str` returns "The {name} voice isn't installed, so {name} can't be read aloud. Run ./run.sh --setup to download it. You can keep practising in text."
- [X] T024 Export exactly the eight public names from `backend/app/practice_languages/__init__.py` via `__all__`, with a module docstring stating that callers import only from here (passes T005's `__all__` test).
- [X] T025 Add `"de_DE-thorsten-medium"` and `"de_DE-kerstin-low"` to the `PIPER_VOICES=( … )` array in `run.sh`, after the two Spanish keys (FR-017; passes T005 I4). Run `./run.sh --setup` once locally and confirm both `.onnx` and `.onnx.json` files land in `~/.local/share/piper-voices`.
- [X] T026 Add the `VoiceChoice` ORM model in the new file `backend/app/models/voice_choice.py`:
  - `__tablename__ = "voice_choices"`;
  - `target_language: Mapped[str] = mapped_column(String(20), primary_key=True)`;
  - `voice_key: Mapped[str] = mapped_column(String(200), nullable=False)`;
  - `updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))`.

  Register it in `init_db()`'s model import list in `backend/app/database.py`. In `backend/app/models/app_settings.py`, change `AppSettings.target_language`'s `default="es"` to `default=DEFAULT_PRACTICE_LANGUAGE`, imported from `app.practice_languages` (analysis I2; required by T100). Add a one-line comment on `AppSettings.tts_voice` in `backend/app/models/app_settings.py`: "Legacy (pre-006): read once by `_seed_voice_choices`; never written."
- [X] T027 Implement `_seed_voice_choices(conn)` in `backend/app/database.py` and call it at the end of `_migrate_db()` (passes T011). It must be ≤ 20 lines, with a helper if needed.
  - Read `target_language, tts_voice` from `app_settings WHERE id = 1`; return if there is no row.
  - Seed only when `tts_voice` is a key in `AVAILABLE_VOICES` whose `.language == target_language`, using `INSERT OR IGNORE INTO voice_choices (target_language, voice_key, updated_at) VALUES (:l, :v, CURRENT_TIMESTAMP)`, then commit.
- [X] T028 Replace `tts_voice: str` in `AppSettingsRecord` with `voice_choices: Mapping[str, str] = field(default_factory=dict)`, and add the abstract `save_voice_choice(self, target_language: str, voice_key: str) -> None`, both in `backend/app/services/storage/base.py` (data-model §6).

  In `backend/app/services/storage/sqlite.py`:
  - load all `VoiceChoice` rows into a `dict` in `_settings_to_record`;
  - implement `save_voice_choice` as a get-or-create upsert with commit.

  This passes T012 and T013.
- [X] T029 Add `class VoiceUnavailable(TTSError)` to `backend/app/services/tts/base.py`, with `__init__(self, user_message: str)` storing `self.user_message`. Add `class VoiceInstallation(ABC)` with the abstract `is_installed(self, voice_key: str) -> bool` in the same file.
- [X] T030 Add `class PiperVoiceInstallation(VoiceInstallation)` to `backend/app/services/tts/piper.py`. Its constructor takes `voice_dir: Path` (expanded). `is_installed` checks that both `<key>.onnx` and `<key>.onnx.json` exist (passes T010, T014).
- [X] T031 Implement `SpeechForLanguage` in the new file `backend/app/services/tts/selection.py`, passing T009. It must not import anything from `app.practice_languages` or `piper`.
  - Its constructor takes `resolve_voice: Callable[[str], str]`, `installation: VoiceInstallation`, `build: Callable[[str], TTSProvider]` and `unavailable_message: Callable[[str], str]`.
  - Methods:
    - `voice_key(language_code)`;
    - `is_available(language_code)`;
    - `provider_for(language_code)`, which raises `VoiceUnavailable(unavailable_message(code))` before calling `build` when the voice is not installed.
- [X] T032 Create the shared test double `backend/tests/support/fake_speech.py` (analysis U1), used by every test that previously overrode `get_tts` or patched `PiperTTSProvider`:
  - `FakeVoiceInstallation(installed: set[str] | None = None)`: every voice is installed when `None`;
  - `RecordingTtsBuilder`, which records `(voice_key, text, output_path)` for each synthesis, writes a tiny valid WAV so `FileResponse` works, and exposes `voice_keys`;
  - `override_speech(app, *, voice_choices=None, installed=None) -> RecordingTtsBuilder`, which sets `app.dependency_overrides` for `get_voice_installation` and `get_speech_for_language`. It builds a real `SpeechForLanguage` with `voice_for` and `voice_unavailable_message`, so production resolution logic stays under test.

  Write `backend/tests/unit/services/test_fake_speech.py` first: the override resolves the German default, records synthesis, and raises `VoiceUnavailable` when a voice is left out of `installed`.
- [X] T033 Wire the factory in `backend/app/services/factory.py`:
  - add `get_voice_installation() -> VoiceInstallation`, returning `PiperVoiceInstallation(get_settings().voice_dir)`;
  - add `get_speech_for_language(app_settings = Depends(get_app_settings), installation = Depends(get_voice_installation)) -> SpeechForLanguage`, with:
    - `resolve_voice=partial(voice_for, voice_choices=app_settings.voice_choices)`;
    - `build=lambda key: PiperTTSProvider(voice_name=key, voice_dir=settings.voice_dir)`;
    - `unavailable_message=voice_unavailable_message`.

  Keep `get_tts` for now, reading `voice_for(app_settings.target_language, app_settings.voice_choices)` instead of the removed `tts_voice`. Its callers migrate in US1 (chat, audio) and US3 (flashcards), and T081 deletes it. Extend `backend/tests/unit/services/test_factory.py` first: `get_speech_for_language` resolves the German choice from `voice_choices`, and `get_tts` no longer reads `tts_voice`.
- [X] T034 Register `@app.exception_handler(VoiceUnavailable)` in `backend/app/main.py`, returning `JSONResponse(status_code=503, content={"detail": exc.user_message})`. Define the status as a named constant next to `LLM_UNAVAILABLE_STATUS` (passes T019).
- [X] T035 Extend `backend/app/routers/settings.py` to pass T015 and T016. Import only `app.practice_languages` and the voice catalogue. Every function must be ≤ 20 lines; extract `_voice_update(req, stored)` and `_language_response(language, app_settings, installation)`.
  - Add `PRACTICE_LANGUAGE_PATTERN = f"^({'|'.join(PRACTICE_LANGUAGES)})$"` and apply it to `UpdateSettingsRequest.target_language`.
  - `_to_response` sets `tts_voice=voice_for(record.target_language, record.voice_choices)`.
  - In `update_settings_endpoint`:
    - pop `tts_voice` from the generic updates;
    - resolve the effective language (`req.target_language or stored.target_language`);
    - raise 422 "Unknown voice." for a key that is not in `AVAILABLE_VOICES`;
    - raise 422 "That voice is for {voice language name}. Choose a {effective language name} voice." on a mismatch;
    - call `storage.save_voice_choice(effective, req.tts_voice)` **only after** all validation (including `_llm_updates`) has passed, so a rejected request writes nothing.
  - Add `language: str` and `is_installed: bool` to `VoiceResponse`. `get_voices_endpoint` takes `installation: VoiceInstallation = Depends(get_voice_installation)`.
  - Add `PracticeLanguageResponse` (the seven fields of contracts §1) and `@router.get("/settings/practice-languages", response_model=list[PracticeLanguageResponse])`, built in catalogue order from `get_app_settings` and `get_voice_installation`.
- [X] T036 Add `target_language_name: str` and `native_language_name: str` to `ConversationResponse` in `backend/app/routers/conversations.py`, filled in `_conv_response` via `ConversationLanguages.of(r.target_language, r.native_language)` (passes T018). `create_conversation` is not modified.
- [X] T037 [P] Write failing tests in `frontend/src/services/api.test.ts`, following the file's fetch-mock pattern:
  - `getPracticeLanguages()` issues `GET /api/settings/practice-languages` and returns the parsed list;
  - a `Conversation` from `getConversation` exposes `target_language_name`.
- [X] T038 Extend `frontend/src/services/api.ts` (passes T037):
  - `export interface PracticeLanguageOption { language_id: string; display_name: string; is_default: boolean; default_voice: string; selected_voice: string; is_voice_installed: boolean; voice_unavailable_message: string | null }`;
  - `export const getPracticeLanguages = (): Promise<PracticeLanguageOption[]>`, next to `getConversationLevels`;
  - add `target_language_name: string` and `native_language_name: string` to `Conversation`;
  - add `language: string` and `is_installed: boolean` to `VoiceOption`.

  Update every typed fixture that `tsc -b` then rejects: `frontend/src/pages/Chat.test.tsx`, `History.test.tsx`, `Settings.test.tsx`, and the component tests using `VoiceOption`. Confirm `npm run build` passes.
- [X] T039 [P] Write `frontend/src/hooks/usePracticeLanguages.test.ts`:
  - it loads the catalogue and the settings, and exposes `{ languages, current, nameOf, isLoading, error }`;
  - `current` is the entry whose `language_id` equals `settings.target_language`;
  - `nameOf('de') === 'German'`, and `nameOf('xx') === 'xx'` (the code is shown, never a crash);
  - a failed load sets `error` and leaves `languages` empty.

  Then implement `frontend/src/hooks/usePracticeLanguages.ts`, shaped like `useConversationLevels.ts`. It lives in the shared `hooks/` folder because Settings, Home and Flashcards all use it (Principle V).
- [X] T040 [P] Extend `frontend/e2e/fixtures.ts` (contracts §10):
  - change `target_language: 'Spanish'` / `native_language: 'English'` to `'es'` / `'en'` in `mockConversation` and `mockSettings`, and add `target_language_name: 'Spanish'` and `native_language_name: 'English'` to `mockConversation`;
  - add `mockPracticeLanguages`: both languages installed, with values matching the backend catalogue;
  - add `mockPracticeLanguagesGermanVoiceMissing`: German `is_voice_installed: false`, with the exact backend message text;
  - add `mockGermanConversation`: id 3, `target_language: 'de'`, `target_language_name: 'German'`;
  - add `mockVoices`: all four voices, with `language` and `is_installed`;
  - add `export async function mockPracticeLanguagesApi(page: Page, languages = mockPracticeLanguages)`, routing `GET /api/settings/practice-languages`;
  - call it from `mockHomeApis` and `mockChatApis`.

  Fix `frontend/e2e/home.spec.ts` (lines 48–49, 89 and 144) to use codes. Run `npm run test:e2e` to confirm that no existing spec regresses.

**Checkpoint**:
- `backend/.venv/bin/pytest` (≥ 90% coverage) and `npm test` pass;
- the catalogue, voice memory, seed and settings API are live;
- nothing the learner sees has changed yet, apart from language validation.

---

## Phase 3: User Story 1: Learner practises a conversation in German (Priority: P1) 🎯 MVP

**Goal**: The learner selects German on Settings and holds a German conversation by text and
speech. Every learning tool and correction mode is German-aware, with explanations in English.

**Independent Test**: Set German, start any scenario, exchange five messages (typed and spoken), and
use each learning tool once (spec US1).
- Automated: T041–T051.
- Model quality: T066–T068 (benchmarks), plus T069 (German on Claude, hand-run).

### Tests for User Story 1 (write first, see them fail)

- [X] T041 [P] [US1] Write `backend/tests/integration/practice_languages/test_language_in_prompts.py` (contracts §5, research R2) for a `de` conversation. Use the recording session provider (`tests/support/recording_session_provider.py`) and a recording `LLMProvider`.
  - The prompts that must contain "German" and "English", and never the bare code (`" de "`, `"in de"`, `"de."`, `" en "`, `"in en"`):
    - the roleplay standing prompt from `POST /chat/{id}/open`, `/message` and `/session`;
    - the opening instruction ("Begin the conversation in German.");
    - the suggestion prompt;
    - the phrasing, word-lookup, translation and grammar prompts;
    - the helper standing prompt;
    - the correction evaluation prompt (Gentle and Strict) and the Gentle recast suffix.
  - The Strict ask-to-repeat note stored for a low-confidence voice message reads "…speak clearly in German." (was "in es").
  - Repeat the same checks for an `es` conversation with "Spanish" (Spanish prompts now name the language too).
  - For **every** scenario from `StaticScenarioProvider.get_all()`, a `de` conversation's standing prompt names German (FR-007).
  - The `de` correction evaluation prompt contains "valid in some region where German is spoken" (spec Edge Case "Regional German") and "capitalisation" in its never-report list (spec Edge Case "German noun capitalisation").
- [X] T042 [P] [US1] Extend `backend/tests/integration/routers/test_learning.py` (contracts §5):
  - each of the four endpoints accepts the trimmed request (`{message_id, content}`, plus `preceding_message` for grammar, and `{message_id, selection, sentence_context}` for word lookup) and builds its prompt from the message's conversation languages;
  - a request with an unknown `message_id` → 404 "Message not found";
  - an old-style request that still sends `target_language`/`native_language` succeeds, and those values are ignored (prove it by sending `"fr"`);
  - the cache behaviour (`cached` true on the second call) is unchanged;
  - 005's level-qualified phrasing key is unchanged.
- [X] T043 [P] [US1] Extend `backend/tests/integration/routers/test_helper.py`:
  - `POST /chat/helper` with `{message, helper_session_id, conversation_id}` for a `de` conversation builds a standing prompt naming German and English;
  - an unknown `conversation_id` → 404;
  - the level rules (005) are still appended.
- [X] T044 [P] [US1] Extend `backend/tests/integration/routers/test_transcribe.py` (contracts §6.1):
  - `language=de` passes `"de"` to the STT fake;
  - `language=fr` → 422 "Unsupported language", and the STT fake is not called;
  - an absent `language` still passes `None`.
- [X] T045 [P] [US1] Extend `backend/tests/integration/routers/test_audio_tts.py` (contracts §6.2). Override `get_voice_installation` and inject a recording builder via `get_speech_for_language`.
  - A message in a `de` conversation is synthesised with a `de_DE-*` key, even while the setting is `es`.
  - A message in an `es` conversation uses the learner's Spanish choice.
  - An uninstalled German voice → 503 with the German `voice_unavailable_message`, and the builder is never called.
  - A cached WAV is served with no voice check.
  - The recording builder asserts voice language == conversation language on every call (FR-018).
- [X] T046 [P] [US1] Extend `backend/tests/integration/routers/test_chat_message.py`:
  - after a reply in a `de` conversation, background synthesis uses a German voice;
  - with the German voice uninstalled, the reply streams normally, **no** synthesis is attempted, `set_tts_path` is not called, and exactly one warning is logged (`caplog`).
- [X] T047 [P] [US1] Write `backend/tests/integration/practice_languages/test_word_audio_language.py` (FR-014, FR-018; analysis C1), using `override_speech` (T032):
  - `GET /api/flashcards/tts/{id}` for a `de` word uses a `de_DE-*` voice while the setting is `es`, and an `es` word uses the learner's Spanish choice while the setting is `de`;
  - with the German voice uninstalled, a `de` word returns 503 with the German `voice_unavailable_message`, and nothing is synthesised;
  - a cached word WAV is served with no voice check.
- [X] T048 [P] [US1] Write `frontend/src/components/settings/PracticeLanguageFieldset.test.tsx`:
  - a `<fieldset>` with the legend "Practice language" and one radio per catalogue language, labelled with `display_name`;
  - reflects `value`, and calls `onChange(language_id)`;
  - one short hint says new conversations use this language and existing ones keep theirs.

  Extend `frontend/src/components/settings/useSettingsForm.test.ts`:
  - loads `practiceLanguage` from `settings.target_language`;
  - `setPracticeLanguage('de')` also sets `ttsVoice` to German's `selected_voice` from the catalogue;
  - `voicesForLanguage` contains only voices whose `language` matches the form's language;
  - `save()` sends `target_language` and `tts_voice` together.
- [X] T049 [P] [US1] Write `frontend/src/components/home/PracticeLanguageNote.test.tsx`: it renders "Practising **German**" (the name in `<strong>`) with a link "Change in Settings" to `/settings`, renders nothing while loading, and renders nothing on a load error (Home stays usable).
- [X] T050 [P] [US1] Write the Chat unit tests:
  - `frontend/src/components/chat/useConversationLanguage.test.ts`: from a `Conversation`, it returns `{ targetCode, targetName, nativeName }`; it returns `isVoiceInstalled` and `voiceUnavailableMessage` for `targetCode` from the practice-languages catalogue; while loading it reports the voice as installed, so audio is never blocked by a slow fetch.
  - `ConversationLanguageTag.test.tsx`: plain text "German" with the accessible name "Conversation language: German", and **no** interactive element.
  - `VoiceUnavailableNotice.test.tsx`: `role="status"` with the given message; renders nothing when the message is null.

  Extend `frontend/src/components/chat/ExpressionHelperPanel.test.tsx`: the label reads "English → German" from `nativeName`/`targetName` props, and `streamHelper` is called with `conversationId`.

  Extend `frontend/src/pages/Chat.test.tsx`:
  - a `de` conversation's recording sends `language=de` while the settings mock says `es`;
  - the header shows "German";
  - with German uninstalled, the notice shows and `AudioPlayer` receives `src={null}`.
- [X] T051 [P] [US1] Write `frontend/e2e/practice-language.spec.ts` (contracts §10):
  - **Settings**: choosing German swaps the Voice list to only "Thorsten (Germany)" and "Kerstin (Germany)", with Thorsten pre-selected. Saving sends `{"target_language": "de", "tts_voice": "de_DE-thorsten-medium", …}` (assert the request body). The level and correction experimental warnings are still visible.
  - **Home**: shows "Practising German" after the settings mock returns `de`.
  - **Chat** for `mockGermanConversation`:
    - the header shows "German", with no `<select>` for language;
    - the helper label is "English → German";
    - the transcribe form data carries `language=de`.
  - **Voice missing**: with `mockPracticeLanguagesGermanVoiceMissing`, the chat shows the status notice with the exact message, and no `/api/audio/tts/*` request is made on the opening reply.

  Extend `frontend/e2e/home.spec.ts` (the note and its link) and `frontend/e2e/settings.spec.ts` (the fieldset appears before "Voice").

### Implementation for User Story 1

- [X] T052 [US1] Name the languages at the chat call sites in `backend/app/routers/chat.py` (passes T041's chat, suggestion and correction rows):
  - `_standing_roleplay_prompt` builds `ConversationLanguages.of(conversation.target_language, conversation.native_language)` and passes `target_name`/`native_name` to `build_roleplay_system_prompt`;
  - `open_chat` passes `target_name` to `build_open_chat_user_prompt`;
  - `_suggestion_prompt` passes `target_name`;
  - `_turn_context` fills `TurnContext.target_language`/`native_language` with the names.

  Add a one-line docstring to `TurnContext` in `backend/app/corrections/services/strategies.py` saying that its language fields are display names used only in prompt text. This is a docstring-only edit; no corrections logic changes.
- [X] T053 [US1] Move the helper to `conversation_id` in `backend/app/routers/chat.py` (passes T043). `HelperRequest` becomes `{message: str, helper_session_id: str, conversation_id: int}`. `chat_helper` gains `storage = Depends(get_storage)`, calls `_require_conversation`, and passes `ConversationLanguages` to `_helper_turn_request`, which calls `build_helper_system_prompt(languages.target_name, languages.native_name)`. Keep `with_learner_text_rules`.
- [X] T054 [US1] Refactor `backend/app/routers/learning.py` to pass T041's learning rows and T042:
  - add `conversation_languages_for_message(storage, message_id) -> ConversationLanguages`, which raises `HTTPException(404, "Message not found")` for a missing message;
  - add `@dataclass(frozen=True) CachedToolRequest(message_id, tool_type, cache_key, prompt)` and `_cached_llm_result(storage, llm, request) -> dict`, replacing the four copies of the `nonlocal computed` closure;
  - drop `native_language` from `TranslateRequest`, `target_language` from `PhrasingRequest`, and both from `WordLookupRequest`;
  - `grammar_check`, `translate`, `alternative_phrasing` and `word_lookup` each resolve languages via the helper, and no longer read `app_settings.target_language` or `app_settings.native_language`. `alternative_phrasing` keeps `get_app_settings` for the level only.

  Each endpoint must be ≤ 20 lines (plan.md function-length plan).
- [X] T055 [US1] Validate the transcription language in `backend/app/routers/audio.py` (passes T044):
  - `_require_supported_language(language)` raises 422 "Unsupported language" when `language is not None and language not in PRACTICE_LANGUAGES`;
  - split `transcribe_audio` (39 lines) into `_require_supported_language`, `_wav_from_upload(file)` and `_transcribe_off_loop(stt, wav_path, language)`, each ≤ 20 lines, with behaviour otherwise unchanged.
- [X] T056 [US1] Move `GET /audio/tts/{message_id}` to `SpeechForLanguage` in `backend/app/routers/audio.py` (passes T045).
  - Replace `tts = Depends(get_tts)` with `speech = Depends(get_speech_for_language)`.
  - Load the message, then its conversation (404 "Conversation not found" if it is missing).
  - Serve the cached WAV if it exists. Otherwise call `speech.provider_for(conversation.target_language).synthesize(...)`; `VoiceUnavailable` propagates to the 503 handler.
  - Split the 24-line function into `_cached_wav(message)` and `_synthesize_and_cache(speech, storage, message, language)`.
  - In the same task, replace the `get_tts` override in `backend/tests/integration/routers/test_audio_tts.py` with `override_speech(...)` from `tests/support/fake_speech.py` (T032).
- [X] T057 [US1] Move chat reply synthesis to `SpeechForLanguage` in `backend/app/routers/chat.py` (passes T046):
  - `_RoleplayContext` holds `speech: SpeechForLanguage` in place of `tts`, and `_roleplay_context` depends on `get_speech_for_language`;
  - `persist` calls `_schedule_tts` only when `speech.is_available(conversation.target_language)`, and otherwise logs one warning naming the language (not the text);
  - `_schedule_tts` takes the provider from `speech.provider_for(...)`.
  - In the same task, move every chat-path test double from `get_tts`/`PiperTTSProvider` to `override_speech(...)` (T032), in: `backend/tests/integration/routers/test_chat_message.py`, `test_chat_open.py`, `test_chat_sessions.py`, `backend/tests/integration/corrections/conftest.py`, `backend/tests/integration/conversation_levels/level_harness.py` (replace `RecordingTTS`) and `backend/tests/integration/test_llm_error_surface.py`. The full backend suite must be green at the end of this task, not only the new tests.
- [X] T058 [US1] Move flashcard word audio to `SpeechForLanguage` now, so the MVP never speaks a word in another language's voice (analysis C1; passes T047).
  - In `backend/app/flashcards/router.py`, `get_vocab_tts` takes `speech: SpeechForLanguage = Depends(get_speech_for_language)` and calls `speech.provider_for(word.target_language)`.
  - Split it into `_cached_word_audio(word)` and `_synthesize_word(speech, storage, word)`, each ≤ 20 lines.
  - Replace the `get_tts` override in `backend/tests/integration/flashcards/conftest.py` with `override_speech(...)`.
- [X] T059 [US1] Update the frontend API client in `frontend/src/services/api.ts`:
  - `translateMessage(messageId, content)`;
  - `getAlternativePhrasing(messageId, content)`;
  - `lookupWord(messageId, selection, sentenceContext?)`;
  - `streamHelper(content, helperSessionId, conversationId, onToken, onDone, onError)`.

  Remove the language arguments and body fields (contracts §5). Update the callers:
  - `frontend/src/components/chat/MessageBubble.tsx` and `LearningToolPanel.tsx` remove their `targetLanguage`/`nativeLanguage` props and pass-throughs;
  - update their tests and `frontend/src/services/api.test.ts` to match.
- [X] T060 [P] [US1] Implement `frontend/src/components/settings/PracticeLanguageFieldset.tsx`, with props `{ languages, value, onChange }`, patterned on `CorrectionModeFieldset.tsx`: native radios, `RadioCard`, `aria-describedby` hint, and tokens only (passes T048's fieldset tests).
- [X] T061 [US1] Extend `frontend/src/components/settings/useSettingsForm.ts` (passes T048's form tests), keeping every function ≤ 20 lines:
  - add `practiceLanguage` to `SettingsValues`, loaded from `target_language` in `toValues` and sent as `target_language` in `toUpdate`;
  - get the catalogue from `usePracticeLanguages()`;
  - `setPracticeLanguage` sets both `practiceLanguage` and `ttsVoice = languages.find(...).selected_voice`;
  - expose `voicesForLanguage = voices.filter(v => v.language === practiceLanguage)`.

  In `frontend/src/pages/Settings.tsx`:
  - render `<PracticeLanguageFieldset>` immediately before `<TtsVoiceField>`;
  - pass `form.voicesForLanguage` to `TtsVoiceField`.

  The page stays declarative layout only; this is the `Settings` row in plan.md § Complexity Tracking.
- [X] T062 [P] [US1] Implement `frontend/src/components/home/PracticeLanguageNote.tsx` using `usePracticeLanguages().current` and a `react-router` `Link` with `className="back-link"`-style muted text (passes T049). Add it to `frontend/src/pages/Home.tsx` directly under the `<nav>`, as one element (plan.md Complexity Tracking).
- [X] T063 [US1] Implement `frontend/src/components/chat/useConversationLanguage.ts`, `ConversationLanguageTag.tsx` and `VoiceUnavailableNotice.tsx` (passes T050's unit tests).

  Update `frontend/src/components/chat/ExpressionHelperPanel.tsx`:
  - it takes `conversationId`, `targetName` and `nativeName` props;
  - its label is `{nativeName} → {targetName}`;
  - it passes `conversationId` to `streamHelper`.
- [X] T064 [US1] Wire the language into `frontend/src/pages/Chat.tsx` (passes T050's Chat tests):
  - keep the loaded `Conversation` in state;
  - replace the `targetLanguage`/`nativeLanguage` `useState`s, and their `setTargetLanguage`/`setNativeLanguage` calls in the settings effect, with `const language = useConversationLanguage(conversation)`;
  - pass `language.targetCode` to `api.transcribeAudio`;
  - render `<ConversationLanguageTag name={language.targetName} />` in the header next to `ConversationLevelControl`;
  - render `<VoiceUnavailableNotice message={language.voiceUnavailableMessage} />` above the messages;
  - render `<AudioPlayer src={language.isVoiceInstalled ? audioState?.src ?? null : null} …/>`;
  - pass `conversationId`, `targetName` and `nativeName` to `ExpressionHelperPanel`.

  No other state, effect or handler is added (plan.md Complexity Tracking).
- [X] T065 [US1] Run `cd frontend && npm run lint && npm run build && npm test && npm run test:e2e`. T051 must now pass, and every pre-existing spec must still pass.

### Benchmarks for User Story 1 (hand-run; research R8, R14)

- [X] T066 [P] [US1] Write `backend/tests/integration/practice_languages/german_evaluation_set.py`:
  - `GERMAN_TURNS`: 10 scenario ids from `StaticScenarioProvider`, each with 5 scripted learner turns in correct, simple German;
  - `DICTATION_SENTENCES`: 20 German sentences, each containing at least one of ä, ö, ü or ß, e.g. "Ich hätte gern einen Kaffee und ein Stück Kuchen, bitte.";
  - `LOANWORD_ALLOWLIST = frozenset({"hotel", "taxi", "ticket", "ok"})`.

  Also write `test_german_evaluation_set.py` (not a benchmark, so it runs in CI) asserting 10 × 5 turns, 20 sentences, and that every sentence has an umlaut or ß.
- [X] T067 [US1] Write `backend/tests/integration/practice_languages/test_german_benchmark.py`, marked `@pytest.mark.benchmark` (SC-002). Model it on `tests/integration/conversation_levels/test_level_benchmark.py`, which drives the real model through `build_llm_provider(LLMSelection(DEFAULT_PROVIDER_ID, …))` and a real `ConversationEngine`. Do **not** use `level_harness.py`: it holds test doubles only.
  - Flag a reply token when `wordfreq.zipf_frequency(t, "de") < 2.0` and `max(zipf(t, "en"), zipf(t, "es")) >= 3.0`, after excluding capitalised mid-sentence tokens (proper nouns) and `LOANWORD_ALLOWLIST`.
  - Write every flagged reply to `specs/006-german-language-support/german-review-sheet.md` for a human verdict.
  - Assert that the unflagged share is ≥ 95%.

  Also write `test_text_purity.py`, which runs in CI, unit-testing the flagging function on fixed strings:
  - "Ich möchte ein Hotel" → no flags;
  - "Ich möchte the menu" → flags "the";
  - "Quiero un café, bitte" → flags "quiero".
- [X] T068 [US1] Write `backend/tests/integration/practice_languages/test_transcription_benchmark.py`, marked `@pytest.mark.benchmark` (SC-003).
  - Synthesise each `DICTATION_SENTENCES` item with `de_DE-kerstin-low` through `PiperTTSProvider` into `tmp_path`, convert it to 16 kHz mono, and transcribe it with `WhisperSTTProvider(get_settings().whisper_model)` and `language_hint="de"`.
  - A sentence passes when every umlaut or ß word appears exactly, and the WER is ≤ 20% after lower-casing and stripping punctuation.
  - Print a table of sentence, transcript, WER and pass. Assert ≥ 18 of 20.
  - Run both benchmarks with `backend/.venv/bin/pytest -m benchmark tests/integration/practice_languages -s`, and record the results in the PR description. If either falls short, add the result to `docs/architecture.md` § "Open items" (quickstart §3) before continuing.
- [X] T069 [US1] Add a German turn to `backend/tests/live/test_claude_code_live.py`, marked `@pytest.mark.claude_live` like the file's existing tests and so deselected by default (FR-026; analysis G1):
  - open a `de` scenario conversation through the real `claude -p` adapter;
  - assert the reply is non-empty and passes the T067 purity check (no flagged non-German word);
  - run it by hand with `backend/.venv/bin/pytest -m claude_live tests/live -k german`, and record the result in the PR description.

**Checkpoint**: A learner can switch to German and hold a full German conversation, with German
speech, German-aware tools, and a plain notice if the voice is missing. This is the MVP.

---

## Phase 4: User Story 2: Switching between Spanish and German without losing anything (Priority: P1)

**Goal**:
- every conversation keeps its own language for every aid, for speech and for saved words,
  whichever language is selected;
- Past Chats labels each conversation's language;
- the Spanish voice choice survives a round trip.

**Independent Test**: With existing Spanish data, switch to German, hold a German conversation,
switch back to Spanish, and continue an older Spanish conversation. All Spanish data is unchanged,
and the continued conversation stays Spanish with a Spanish voice (spec US2).

### Tests for User Story 2 (write first, see them fail)

- [X] T070 [P] [US2] Write `backend/tests/integration/practice_languages/test_conversation_language.py` (FR-006, FR-009, FR-014, FR-019, FR-025; US2-2, US2-3).
  - Fixture: an `es` conversation with messages, stored while the setting is `es`. Then `PUT {"target_language": "de"}`.
  - Assert, one test each:
    - `open`/`message`/`session` on the `es` conversation build Spanish standing prompts;
    - suggestions, phrasing, word lookup, translation, grammar and the helper (by `conversation_id`) all name Spanish;
    - the reply is synthesised with a `es_*` voice (recording builder);
    - `POST /vocabulary` with `source_conversation_id` of the `es` conversation saves a word with `target_language == "es"`;
    - `POST /vocabulary` without `source_conversation_id` saves `"de"` (the practice language);
    - `POST /vocabulary` with an unknown `source_conversation_id` → 404 "Conversation not found";
    - a new conversation created now is `de`;
    - no pre-existing conversation, message or vocabulary row changed (compare snapshots).
- [X] T071 [P] [US2] Extend `backend/tests/integration/routers/test_vocabulary.py` (contracts §7):
  - "Straße", "Übung" and "schön" round-trip byte-exact through save → `GET /vocabulary`;
  - "Haus" saved from a `de` conversation and from an `es` conversation gives two rows with different ids and languages (FR-023);
  - a second save of "Haus" from the same `de` conversation returns 200 `already_saved: true`;
  - "Haus" and "haus" are distinct, because nothing folds case (research R12).
- [X] T072 [P] [US2] Extend `frontend/src/pages/History.test.tsx`, then `frontend/e2e/history.spec.ts`: with `mockConversation` (Spanish) and `mockGermanConversation` in the list, each row shows its language name ("Spanish", "German") as text next to the title, and the name is part of the row's accessible name (FR-012).
- [X] T073 [P] [US2] Extend `frontend/e2e/practice-language.spec.ts`:
  - **Round trip**: switch Settings to German and save, then back to Spanish, and the Voice list shows the Spanish voices with `es_AR-daniela-high` selected (the mock's Spanish `selected_voice`; US2-4).
  - **Older conversation**: with the settings mock at `de`, opening `mockConversation` (Spanish) shows the "Spanish" tag, the helper label "English → Spanish", and a transcribe request carrying `language=es` (US2-2).

### Implementation for User Story 2

- [X] T074 [US2] Derive the saved word's languages from the source conversation in `backend/app/routers/vocabulary.py` (passes T070's vocabulary rows and T071):
  - `_word_languages(storage, req, app_settings) -> tuple[str, str]` returns the source conversation's `(target_language, native_language)`, raises 404 when the id is unknown, and falls back to `app_settings.target_language`/`native_language` when no id is given;
  - `_save_response(item)` builds the response;
  - `save_vocabulary` must be ≤ 20 lines.
- [X] T075 [US2] Render `conv.target_language_name` in each Past Chats row in `frontend/src/pages/History.tsx` as a muted tag. Use `--color-text-muted`, `--radius-lg` and a border token; no new colour (passes T072).
- [X] T076 [US2] Run the full backend and frontend suites. T070–T073 must pass. Confirm T017 (SC-005) still passes.

**Checkpoint**: Spanish and German can be alternated freely. Each conversation is self-consistent,
and nothing is rewritten.

---

## Phase 5: User Story 3: Learner studies German vocabulary with flashcards (Priority: P2)

**Goal**:
- the word list, decks, deck generation, practice and analytics show only the practice language;
- German words play in a German voice, with German word details written in English;
- existing data belongs to Spanish.

**Independent Test**: Save three German words, generate a deck and practise it with German selected:
only those words appear, with German audio and details. Switch to Spanish: only Spanish words,
decks and statistics (spec US3).

### Tests for User Story 3 (write first, see them fail)

- [X] T077 [P] [US3] Extend `backend/tests/unit/test_database.py` (data-model §7):
  - `_ADDITIVE_COLUMNS` ends with `("decks", "target_language VARCHAR(20) NOT NULL DEFAULT 'es'")` then `("practice_sessions", "target_language VARCHAR(20) NOT NULL DEFAULT 'es'")`;
  - migrating a database that has a deck and a session without the column leaves both reading `'es'` (FR-021).

  Extend T017's `backend/tests/integration/practice_languages/test_upgrade_preserves_data.py` so the pre-006 fixture (built from `schema_005.sql`, whose `decks` and `practice_sessions` have no `target_language`) also holds two decks with cards, one completed session with card results and a classification snapshot. After the double `init_db()`:
  - those rows are unchanged in their pre-006 columns;
  - both new columns read `es`;
  - `GET /api/flashcards/decks?language=es` lists both decks.
- [X] T078 [P] [US3] Extend `backend/tests/contract/service_interfaces/test_flashcard_storage_provider.py`:
  - `list_words`, `list_decks`, `create_deck`, `get_sessions_since`, `get_card_results_since`, `get_classification_counts` and `get_classification_snapshots_since` each require the keyword-only `language` parameter (calling without it raises `TypeError`);
  - `DeckRecord` and `SessionRecord` have `target_language`.
- [X] T079 [P] [US3] Extend `backend/tests/unit/flashcards/test_word_library.py` and `backend/tests/unit/flashcards/test_analytics_service.py` against a fake or SQLite storage seeded with es and de words, decks, sessions, results and snapshots:
  - each storage method returns only its language's rows;
  - `create_session` copies the deck's language;
  - deleting the deck leaves the session's `target_language` intact;
  - `AnalyticsService(storage, "de").build_summary("all")` counts only German figures, including `current_streak` (a day with only Spanish practice does not count) and `sessions_this_week`.
- [X] T080 [P] [US3] Extend `backend/tests/unit/flashcards/test_llm_cache.py`: the fill-blank and word-info prompts for a `de` word contain "German" and "English" and no bare codes. The cache slot is still keyed by the code (`language="de"`).
- [X] T081 [P] [US3] Write `backend/tests/integration/practice_languages/test_flashcards_by_language.py` (contracts §8, SC-006) with mixed es/de fixtures:
  - `GET /api/flashcards/words?language=de`, `/decks?language=de` and `/analytics?language=de&range=all` contain no `es` word, deck, session, result or snapshot count, and vice versa;
  - each of those GETs without `language`, or with `language=fr` → 422;
  - `POST /decks` with `language=de`: the `all` and `filtered` sources draw only German words; `selected_word_ids` including an `es` word → 422 "Some selected words are in another language. Reload the word list."; the response has `target_language: "de"`;
  - `POST /decks/{es_deck}/refresh` while the setting is `de` draws Spanish words;
  - **in-progress session**: start a session on an `es` deck, set `target_language` to `de`, record a card, end the session. The snapshot counts only Spanish words, the summary streak counts Spanish sessions, and `POST /sessions/{id}/missed-deck` creates an `es` deck;
  - the same spelling in both languages has separate classifications and LLM-cache rows (FR-023).

  Update the existing `backend/tests/integration/flashcards/test_*_endpoints.py` calls to pass `language=es`.
- [X] T082 [P] [US3] Write the frontend flashcards tests:
  - `frontend/src/hooks/flashcards/useWordLibrary.test.ts`, `useDecks.test.ts` and `useFlashcardAnalytics.test.ts`: each passes `usePracticeLanguages().current.language_id` to the API call, includes it in the query key, and does not fetch until the language is known.
  - Extend `frontend/src/services/flashcardsApi.test.ts`:
    - `fetchWords(language, filters)`, `listDecks(language)` and `fetchAnalytics(language, range)` send `language=` as a query parameter;
    - `createDeck({...payload, language})` sends it in the body;
    - `describeAudioFailure(url)` returns the JSON `detail` of a 503, and a generic "Audio is unavailable for this word." otherwise.
  - Write `frontend/src/components/flashcards/useWordAudio.test.ts`: `play(rate)` plays; on an audio error it sets `failureMessage` from `describeAudioFailure`.
  - Extend `AudioControls.test.tsx`: the failure message renders with `role="status"`.
- [X] T083 [P] [US3] Extend `frontend/e2e/flashcards.spec.ts`, `flashcard-practice.spec.ts` and `flashcard-analytics.spec.ts`, with a new fixture helper `mockPracticeLanguageSetting(page, 'es' | 'de')` in `frontend/e2e/fixtures.ts`.
  - Change the `target_language: 'fr'` word fixtures to `'es'`, and add German word fixtures.
  - Every `/api/flashcards/words`, `/decks` and `/analytics` request carries `language=<setting>`. Assert it in the route handler.
  - Change the exact-match route `'/api/flashcards/decks'` (flashcards.spec.ts:251) to a predicate matching the path with any query string, so that it does not also match `/decks/{id}`.
  - With the setting `de`, only German words and decks render. Switching the setting to `es` and reopening the page never shows a German item, not even briefly: assert with `expect(...).toHaveCount(0)` immediately after navigation.
  - A 503 on `/api/flashcards/tts/*` shows the German voice message.

### Implementation for User Story 3

- [X] T084 [US3] Add `target_language: Mapped[str] = mapped_column(String(20), nullable=False)`, with **no** Python default, to `Deck` and `PracticeSession` in `backend/app/flashcards/models.py`. Append the two entries to `_ADDITIVE_COLUMNS` in `backend/app/database.py`, exactly `"target_language VARCHAR(20) NOT NULL DEFAULT 'es'"`, with the default built from `DEFAULT_PRACTICE_LANGUAGE` (passes T077).
- [X] T085 [US3] Update the flashcard storage in `backend/app/flashcards/services/storage.py` and `sqlite_storage.py` (passes T078 and the storage parts of T079):
  - add `target_language: str` to `DeckRecord` and `SessionRecord`, and copy it in `_deck_to_record` and `_session_to_record`;
  - add the required keyword-only `language: str` to the seven methods in data-model §8, in both the ABC and SQLite;
  - `create_session` reads the deck's language via `_deck_language(deck_id)`;
  - `get_card_results_since` and `get_classification_snapshots_since` join `PracticeSession` on `session_id` and filter `PracticeSession.target_language == language`;
  - bring `create_deck` (33 lines) under 20 with `_insert_cards(deck_id, cards)`, and `list_words` with `_filtered_word_query(...)`.
- [X] T086 [US3] Update the flashcard services (passes the service parts of T079):
  - `AnalyticsService.__init__(self, storage, language: str)` passes `language=self._language` to every storage call, in `backend/app/flashcards/services/analytics.py`;
  - bring `hardest_words` (29 lines) under 20 with `_tally_by_word(results)` and `_hardest_candidate(vocab_id, counts)`;
  - in `backend/app/flashcards/services/session.py`, `SessionService._snapshot_classifications` and `_calculate_streak` use the session's `target_language` (load the session once, then pass the language down).
- [X] T087 [US3] Use language names in `LlmCacheService._generate_sentence` and `_generate_content` in `backend/app/flashcards/services/llm_cache.py`: `language_name(language)` and `language_name(native_language)` in the prompt text, while the `_CacheSlot` keeps the code (passes T080). Import from `app.practice_languages` only.
- [X] T088 [US3] Update `backend/app/flashcards/schemas.py`: `language: str = Field(..., pattern=PRACTICE_LANGUAGE_PATTERN)` on `DeckConfigRequest`, and `target_language: str` on `DeckDetail` and `DeckSummary`. Build the pattern from `PRACTICE_LANGUAGES` in the flashcards module; do not import it from `routers/settings.py`.
- [X] T089 [US3] Update `backend/app/flashcards/router.py` (passes T081), bringing every function listed for this file in plan.md § "Function-length plan" under 20 lines as it is touched:
  - `get_words`, `list_decks` and `get_analytics` take `language: str = Query(..., pattern=…)`;
  - `create_deck` passes `body.language` to the pool and to `storage.create_deck`, with `_require_same_language(words, language)` raising the 422;
  - `refresh_deck` passes `deck.target_language`;
  - `create_missed_deck` passes `session.target_language`;
  - `get_analytics` constructs `AnalyticsService(storage, language)`;
  - `_build_deck_detail` and `_deck_summary` set `target_language`.
  - Extractions: `_word_list_item`, `_deck_word_pool`, `_require_same_language`, `_deck_name`, `_deck_summary`, `_learned_card_ids`, `_refresh_candidates`, `_missed_word_ids` and `_missed_deck_cards`.
- [X] T090 [US3] Delete `get_tts` from `backend/app/services/factory.py`, and its test cases from `backend/tests/unit/services/test_factory.py`. Its three callers were moved in T056, T057 and T058. `grep -rn "get_tts\b" backend/app backend/tests` must return nothing, and the full backend suite must pass.
- [X] T091 [US3] Update the frontend flashcards API and hooks (passes T082's API and hook tests):
  - in `frontend/src/services/flashcardsApi.ts`: `fetchWords(language, filters)`, `listDecks(language)`, `fetchAnalytics(language, range)`, `language` in `DeckConfigPayload`, `target_language` on `DeckSummary`/`DeckDetail`, and `describeAudioFailure(url)`;
  - implement `frontend/src/hooks/flashcards/useWordLibrary.ts`, `useDecks.ts` and `useFlashcardAnalytics.ts`, each with the query keys `['flashcard-words', language, filters]`, `['flashcard-decks', language]` and `['analytics', language, range]` and `enabled: !!language`.
- [X] T092 [US3] Replace the inline `useQuery` calls with the hooks, keeping existing `invalidateQueries` calls working with the prefix keys:
  - `frontend/src/pages/Flashcards.tsx` uses `useWordLibrary(filters)`;
  - `frontend/src/pages/FlashcardDecks.tsx` uses `useDecks()`;
  - `frontend/src/pages/FlashcardAnalytics.tsx` uses `useFlashcardAnalytics(range)`.

  In `frontend/src/components/flashcards/DeckConfigPanel.tsx`, add `language: current.language_id` from `usePracticeLanguages()` to the `createDeck` payload. Each page change is the one hook swap recorded in plan.md Complexity Tracking.
- [X] T093 [US3] Split `frontend/src/components/flashcards/AudioControls.tsx` (52 lines) into a `useWordAudio(ttsUrl)` hook (in `components/flashcards/useWordAudio.ts`) and an `AudioFailureMessage` component (`role="status"`, muted token text). Every function must be ≤ 20 lines, and the two buttons are unchanged (passes T082's audio tests).
- [X] T094 [US3] Run the full backend and frontend suites. T077–T083 must pass, along with every pre-existing flashcards test and E2E spec.

**Checkpoint**: Flashcards are fully per-language. Existing decks and history sit under Spanish, and
a session in progress finishes in its own language.

---

## Phase 6: User Story 4: Learner chooses a German voice (Priority: P3)

**Goal**: With German selected, Settings lists only German voices, one of them pre-selected. The
chosen voice is used for the next reply and for flashcards, and an uninstalled voice is flagged.

**Independent Test**: Select German in Settings. The voice list shows only German voices with one
selected, and the chosen voice is used for the next partner reply (spec US4).

### Tests for User Story 4 (write first, see them fail)

- [X] T095 [P] [US4] Extend `backend/tests/integration/routers/test_audio_tts.py`: after `PUT {"target_language": "de", "tts_voice": "de_DE-kerstin-low"}`, the next German message is synthesised with `de_DE-kerstin-low`, and a German flashcard word (`GET /flashcards/tts/{id}`) uses it too (US4-2).
- [X] T096 [P] [US4] Extend `frontend/src/components/settings/TtsVoiceField.test.tsx`: when the selected voice has `is_installed: false`, the hint "Not installed. Run ./run.sh --setup to download it." renders with `role="status"`, and it is linked from the `<select>` via `aria-describedby`. Installed voices show no hint.
- [X] T097 [P] [US4] Extend `frontend/e2e/practice-language.spec.ts`:
  - with German selected, choose "Kerstin (Germany)", Save, and the PUT body carries `"tts_voice": "de_DE-kerstin-low"`;
  - reloading Settings shows Kerstin selected (the mocked `selected_voice`);
  - with `mockVoices` marking Kerstin `is_installed: false`, the not-installed hint shows.

### Implementation for User Story 4

- [X] T098 [US4] Add the not-installed hint to `frontend/src/components/settings/TtsVoiceField.tsx` (passes T096). `VoiceDetails` gains the hint row, wired with `aria-describedby` on the select, with every function ≤ 20 lines.
- [X] T099 [US4] Run the suites. T095–T097 must pass. Confirm manually (quickstart §4 step 1) that the next German reply is spoken by the chosen voice.

**Checkpoint**: All four stories work independently.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Guards, documentation and validation across all stories.

- [ ] T100 [P] Write `backend/tests/unit/test_no_language_literals.py` (plan.md Constitution Check, principle V row):
  - scan `backend/app/**/*.py` for the quoted literals `"es"`, `'es'`, `"de"`, `'de'`;
  - allow only `backend/app/practice_languages/catalog.py` and `backend/app/services/tts/voices.py`. Every other default, including `AppSettings.target_language` (T026) and the `_ADDITIVE_COLUMNS` entries (T084), uses `DEFAULT_PRACTICE_LANGUAGE`, never a literal;
  - fail with the file and line of any other hit.

  Do the same for `frontend/src/**/*.{ts,tsx}`, excluding `*.test.*`.
- [ ] T101 [P] Update `docs/architecture.md`:
  - a "Practice languages" section covering the catalogue, codes vs names (research R2), per-language voices, `SpeechForLanguage`, and flashcards scoped by an explicit `language` parameter;
  - § "Open items": the SC-002 and SC-003 benchmark results from T067–T068, and the ASCII-only word-search limitation (research R12).
- [ ] T102 [P] Update `README.md`: the voice table gains the two German voices, the setup section says that `./run.sh --setup` downloads Spanish and German voices, and the `OPEN_LANGUAGE_TTS_VOICE` row notes that the voice is now chosen per language in Settings. Mention the same in `.env.example` next to `OPEN_LANGUAGE_TTS_VOICE`.
- [ ] T103 [P] Update `CLAUDE.md`:
  - add a "006-german-language-support" entry to Recent Changes;
  - add `backend/app/practice_languages/` to "Domain modules", with the note that it is the only place a language code becomes a name or a default voice;
  - point "read the current plan" at `specs/006-german-language-support/plan.md`.
- [ ] T104 Run the manual accessibility check (quickstart §5) on Settings, Home, Chat and Past Chats in light and dark themes:
  - the radios are keyboard-operable, with the group announced;
  - the notice and hint are announced;
  - tags pass contrast;
  - targets are ≥ 44 px.

  Record the result in the PR description.
- [ ] T105 Run quickstart.md §1–§5 end to end. Quickstart §4 steps 1–7 are the SC-004 feature checklist; run them once with Ollama and once with Claude selected (FR-026):
  - including the SC-005 comparison after step 8, against the T003 backup;
  - the offline check (SC-007);
  - the voice-missing check (FR-018);
  - the SC-001 stopwatch.

  Record each SC's result in the PR description.
- [ ] T106 Final gate. From `backend/`: `backend/.venv/bin/pytest` (≥ 90% coverage, zero skips), `backend/.venv/bin/ruff check .` and `backend/.venv/bin/black --check .`. From `frontend/`: `npm run lint`, `npm run build`, `npm test` and `npm run test:e2e`. All must pass with zero failures.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies. T003 must run before any 006 code starts the app.
- **Foundational (Phase 2)**: depends on Setup. **It blocks every story.**
- **US1 (Phase 3)**: depends on Foundational.
- **US2 (Phase 4)**: depends on Foundational, and on US1's T053/T054 (learning aids resolved from the conversation) and T063/T064 (Chat language hook). US2 asserts the cross-switch behaviour of code US1 introduces.
- **US3 (Phase 5)**: depends on Foundational only. It can run in parallel with US1 and US2 if staffed. Its T090 (delete `get_tts`) must come after US1's T056, T057 and T058.
- **US4 (Phase 6)**: depends on Foundational and US1's T061 (the Settings form follows the language).
- **Polish (Phase 7)**: depends on all stories. T101 needs the benchmark results from T067 and T068.

### Within the Foundational phase

- The tests T005–T019 run in parallel, and all fail first.
- Catalogue chain: T020 → T021 → T022 → T023 → T024. T025 needs T022.
- Storage chain: T026 → T027 and T028. The seed needs the model, and T028 needs the model.
- TTS chain: T029 → T030, T031 → T032 → T033. The factory needs T023 and T028. T034 needs T029.
- T035 needs T023, T028 and T033. T036 needs T021.
- Frontend: T037 → T038 → T039. T040 is independent of T039.

### Within each story

- Test tasks first; confirm they fail.
- Backend before the frontend that calls it. For example, T059 (API client) comes after T053 and T054.
- Pages last. For example, T064 comes after T063, and T092 after T091.
- Each story ends with a full-suite run (T065, T076, T094, T099).

### Parallel Opportunities

- Setup: T001 runs alongside T002. T004 can run at any time before T017.
- Foundational: all 15 test tasks (T005–T019), and T037, T039 and T040.
- US1: the tests T041–T051 together; T060 and T062 alongside the backend work T052–T058; the benchmark set T066 at any time.
- US2: T070–T073 together.
- US3: T077–T083 together. The frontend T091–T093 can run alongside the backend T085–T090 once T088 has fixed the schemas.
- US3 as a whole can run in parallel with US1 and US2, apart from the T090 ordering above. T058 (US1) and T089 (US3) both edit `backend/app/flashcards/router.py`, so do not run them at the same time.

---

## Parallel Example: User Story 1

```bash
# All US1 tests together (each must fail first):
Task: "T041 language names in every prompt — backend/tests/integration/practice_languages/test_language_in_prompts.py"
Task: "T042 learning endpoints resolve from the conversation — backend/tests/integration/routers/test_learning.py"
Task: "T044 transcribe language validation — backend/tests/integration/routers/test_transcribe.py"
Task: "T045 TTS by conversation language, 503 — backend/tests/integration/routers/test_audio_tts.py"
Task: "T048 PracticeLanguageFieldset + useSettingsForm — frontend/src/components/settings/"
Task: "T051 practice-language E2E — frontend/e2e/practice-language.spec.ts"

# Independent implementation files together:
Task: "T060 PracticeLanguageFieldset.tsx"
Task: "T062 PracticeLanguageNote.tsx + Home"
Task: "T066 german_evaluation_set.py"
```

## Parallel Example: User Story 3

```bash
Task: "T078 storage ABC contract — backend/tests/contract/service_interfaces/test_flashcard_storage_provider.py"
Task: "T081 per-language endpoints — backend/tests/integration/practice_languages/test_flashcards_by_language.py"
Task: "T082 flashcards hooks, API, audio — frontend/src/hooks/flashcards/, frontend/src/services/flashcardsApi.test.ts"
Task: "T083 flashcards E2E — frontend/e2e/flashcards*.spec.ts"
```

---

## Implementation Strategy

### MVP first (User Story 1)

1. Phase 1 Setup, including the database backup (T003).
2. Phase 2 Foundational. At its checkpoint nothing visible has changed except validation.
3. Phase 3 US1, **including the benchmarks T066–T068**. Run them before building further, so that
   an adherence or transcription shortfall is known early (research R8, R14).
4. **Stop and validate**: quickstart §4 steps 1–7.

### Incremental delivery

1. Foundation → US1 (German conversation) → demo.
2. + US2: switching is safe, and Past Chats shows each language.
3. + US3: per-language flashcards.
4. + US4: voice choice polish.
5. Polish: docs, guards, accessibility, and full quickstart validation.

---

## Notes

- **[P]** means a different file with no dependency on an incomplete task. Two [P] tasks never edit
  the same file.
- Every test must be seen failing before its implementation (Red → Green → Refactor).
- The benchmarks (T067, T068) are **deselected** by the existing `-m 'not benchmark …'` addopts, not
  skipped. `test_german_evaluation_set.py` and `test_text_purity.py` run in CI.
- Commit after each task or logical group, ending commit messages with the attribution line required
  by the session.
