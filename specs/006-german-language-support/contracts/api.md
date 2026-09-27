# Interface Contracts: German Language Support

**Feature**: [spec.md](../spec.md) | **Data model**: [data-model.md](../data-model.md) |
**Research**: [research.md](../research.md)

All paths are under `/api`. Unless a section says otherwise, the request and response shapes of
existing endpoints are unchanged. Language values on the wire are catalogue codes (`es`, `de`).
Display names travel only in fields whose names end in `_name`, or in `display_name`.

Changes by section: **§1 new**, **§2–§4 extended**, **§5 learning aids**, **§6 speech**,
**§7 vocabulary**, **§8 flashcards**, **§9 module interfaces**, **§10 UI and E2E**.

---

## 1. `GET /api/settings/practice-languages` (new)

Returns the catalogue in display order, with the learner's voice for each language and whether that
voice is installed. It takes no parameters.

**200**

```json
[
  {
    "language_id": "es",
    "display_name": "Spanish",
    "is_default": true,
    "default_voice": "es_ES-davefx-medium",
    "selected_voice": "es_AR-daniela-high",
    "is_voice_installed": true,
    "voice_unavailable_message": null
  },
  {
    "language_id": "de",
    "display_name": "German",
    "is_default": false,
    "default_voice": "de_DE-thorsten-medium",
    "selected_voice": "de_DE-thorsten-medium",
    "is_voice_installed": false,
    "voice_unavailable_message": "The German voice isn't installed, so German can't be read aloud. Run ./run.sh --setup to download it. You can keep practising in text."
  }
]
```

| Guarantee | Test |
|---|---|
| Exactly the `PRACTICE_LANGUAGES` entries, in catalogue order, and exactly one `is_default` | contract |
| `language_id` values equal the values `PUT /api/settings` accepts for `target_language` | contract (both derived from the catalogue) |
| `selected_voice` = `voice_for(code, voice_choices)`, which always belongs to that language | integration: a mismatched stored choice resolves to the default |
| `voice_unavailable_message` is non-null exactly when `is_voice_installed` is false | contract |
| The installation check goes through `VoiceInstallation` (a fake in tests, no files needed) | integration |

## 2. `GET /api/settings` and `PUT /api/settings` (extended)

**`SettingsResponse`**: same fields.
- `target_language` is the practice language.
- `tts_voice` is now **derived**: the voice for the current `target_language`
  (`voice_for(target_language, voice_choices)`).

**`UpdateSettingsRequest`**:
- `target_language` gains a pattern built from the catalogue (`^(es|de)$`).
- `tts_voice` is now validated and stored **for the practice language in effect after this update**:
  the request's `target_language` if present, otherwise the stored one.

| Case | Result |
|---|---|
| `{"target_language": "de"}` | **200**. The practice language is `de`. The response `tts_voice` is German's remembered voice, or its default. The Spanish choice is untouched (FR-016). |
| `{"target_language": "de", "tts_voice": "de_DE-kerstin-low"}` | **200**. The voice is remembered for `de`. |
| `{"tts_voice": "de_DE-kerstin-low"}` while the stored language is `es` | **422**: "That voice is for German. Choose a Spanish voice." Nothing is written. |
| `{"tts_voice": "xx_XX-nope-low"}` | **422**: "Unknown voice." Nothing is written. |
| `{"target_language": "fr"}` | **422** (pattern). Nothing is written. |
| `{"target_language": "es"}` after using German | **200**. The response `tts_voice` is the learner's earlier Spanish choice (US2-4). |
| A language change and an LLM change in one request | Both apply. The provider validation (004 `_llm_updates`) is unchanged, and the language never changes the provider (FR-026). |
| Any change | No existing conversation, word, deck or session is modified (FR-025): integration assertion |

## 3. `GET /api/settings/voices` (extended)

Each `VoiceResponse` gains two fields:

```json
{ "key": "de_DE-thorsten-medium", "…": "…", "language": "de", "is_installed": true }
```

The endpoint returns all four catalogue voices. The Settings form filters them by the selected
language on the client (FR-015); the list is small and static.

## 4. Conversations (extended)

**`ConversationResponse`** (list, get, create and patch) gains:

```json
{ "target_language": "de", "native_language": "en",
  "target_language_name": "German", "native_language_name": "English" }
```

- `POST /api/conversations` takes the same request, and still stamps
  `target_language = app_settings.target_language` (FR-006).
- Past Chats reads `target_language_name` (FR-012).
- Chat reads both names for its header tag and the helper label, "English → German" (FR-011).

| Guarantee | Test |
|---|---|
| A conversation created while German is selected has `target_language == "de"` | integration |
| Changing the practice language afterwards leaves that conversation's language unchanged | integration (US2-3) |
| Every stored conversation lists with its own language name | integration (mixed fixture) |

## 5. Learning aids resolve languages from the conversation (FR-009)

The request models **drop** their language fields. Pydantic ignores unknown fields, so old clients
still work. Each endpoint resolves `ConversationLanguages` from `message_id` → message →
conversation. If the message does not exist, the result is **404** "Message not found".

| Endpoint | Request after | Languages used |
|---|---|---|
| `POST /learning/grammar` | `{message_id, content, preceding_message?}` | native name from the conversation |
| `POST /learning/translate` | `{message_id, content}` | native name from the conversation |
| `POST /learning/phrasing` | `{message_id, content}` | target name from the conversation; the level rules (005) are unchanged |
| `POST /learning/word-lookup` | `{message_id, selection, sentence_context?}` | both names from the conversation |
| `POST /chat/helper` | `{message, helper_session_id, conversation_id}` | both names from the conversation. An unknown `conversation_id` is **404** |

Cache keys (`get_or_create_learning_result`) are unchanged. A message belongs to exactly one
conversation, so its language cannot vary under the same key.

| Guarantee | Test |
|---|---|
| With German selected, a phrasing, lookup, translation, grammar or helper request on a **Spanish** conversation's message builds a prompt naming Spanish | integration, one per endpoint (FR-009) |
| Prompts name languages ("German"), never codes (`de`) | integration: assert `"German"` is present and `" de "` / `"in de"` are absent (research R2) |
| The roleplay standing prompt, open instruction, suggestion prompt, correction evaluation, recast and repeat request all carry the conversation's language name | integration (FR-008) |
| Explanations stay in English: every prompt's native-language slot is "English" | integration (FR-010) |

## 6. Speech

### 6.1 `POST /api/audio/transcribe` (validated)

- The multipart `language` field, when present, must be a catalogue code. Otherwise the result is
  **422** "Unsupported language".
- When absent, behaviour is unchanged (auto-detect). The Chat page always sends the
  **conversation's** code (research R7).
- The response shape is unchanged.

### 6.2 `GET /api/audio/tts/{message_id}` and `GET /api/flashcards/tts/{vocabulary_item_id}` (changed)

| Case | Result |
|---|---|
| The text's language voice is installed | **200** `audio/wav`, synthesised with `voice_for(language, choices)`. The language is the message's conversation language, or the word's `target_language`. |
| The voice is not installed | **503** `{"detail": "<voice_unavailable_message>"}`. **Nothing is synthesised with another voice** (FR-018). |
| A cached WAV exists | **200**, served as today, with no voice check |

In chat, background synthesis after a reply skips synthesis when the voice is not installed, and
logs one warning. It no longer fails invisibly in the executor.

| Guarantee | Test |
|---|---|
| A German reply is synthesised by a provider built for `de_DE-*`, even while Spanish is selected (and the reverse) | integration with a recording TTS builder (FR-014, US2-2) |
| No code path passes a voice of language X to text of language Y | integration: the recording builder asserts voice language == text language |
| Unavailable → 503 with the plain message, and the builder is never called | integration |

## 7. `POST /api/vocabulary` (changed)

The request and response shapes are unchanged. The saved word's `target_language` and
`native_language` come from `source_conversation_id`'s conversation (FR-019). If
`source_conversation_id` is absent, the practice language is used. If it is present but unknown,
the result is **404** "Conversation not found".

| Guarantee | Test |
|---|---|
| A word saved from a Spanish conversation while German is selected is Spanish | integration |
| "Haus" (de) and "Haus" (es) are two rows, each with its own classification and LLM cache | integration (FR-023) |
| "Straße", "Übung" and "schön" round-trip byte-exact through save → list → deck → TTS text | integration (spec Edge Cases) |

## 8. Flashcards (`/api/flashcards/*`)

| Endpoint | Change |
|---|---|
| `GET /words?language=de&…` | **`language` required**. Only that language's words. |
| `GET /decks?language=de` | **`language` required**. Only that language's decks. |
| `POST /decks` | Body gains **required** `language`. The pool, `filtered` and `all` sources draw only from it. `selected` ids in another language → **422** "Some selected words are in another language. Reload the word list." |
| `GET /analytics?language=de&range=7d` | **`language` required**. Every figure is computed from that language's words and sessions: at-a-glance, streak, trend, activity, snapshots, hardest words, recently learned, mode performance. |
| `DeckSummary`, `DeckDetail` | Gain `target_language` |
| `POST /decks/{id}/refresh` | Draws from the deck's own language |
| `POST /sessions` | The session copies the deck's language |
| `POST /sessions/{id}/end`, `GET /sessions/{id}/summary`, `POST /sessions/{id}/missed-deck` | Use the **session's** language (snapshot, streak, and the missed deck's language), whatever the setting is |
| `GET /words/{id}/info/{type}`, `GET /tts/{id}` | Use the word's language (unchanged key; prompts now name the language, research R2) |

A missing or unknown `language` on the three GET collection endpoints and on `POST /decks` → **422**.

| Guarantee | Test |
|---|---|
| With mixed es/de fixtures, no response under `language=de` contains an `es` word, deck, session, result or snapshot count, and vice versa | integration (SC-006) |
| Pre-006 decks and sessions list under `language=es` | integration (FR-021) |
| Ending a Spanish session while the setting is `de` snapshots Spanish counts | integration (edge case) |

## 9. Module interfaces (Python)

### `app.practice_languages` (new; routers import only the package root)

```python
PracticeLanguage          # frozen: code, name, default_voice
PRACTICE_LANGUAGES: Mapping[str, PracticeLanguage]
DEFAULT_PRACTICE_LANGUAGE: str                        # "es"
class UnknownLanguage(ValueError): ...
def language_name(code: str) -> str: ...              # practice or native; raises UnknownLanguage
class ConversationLanguages:                          # target_code, target_name, native_name
    @classmethod
    def of(cls, target_code: str, native_code: str) -> "ConversationLanguages": ...
def voice_for(code: str, voice_choices: Mapping[str, str]) -> str: ...
def voice_unavailable_message(code: str) -> str: ...
```

### `app.services.tts` (extended)

```python
class VoiceUnavailable(TTSError):          # .user_message
class VoiceInstallation(ABC):
    def is_installed(self, voice_key: str) -> bool: ...
class PiperVoiceInstallation(VoiceInstallation): ...          # services/tts/piper.py
class SpeechForLanguage:                                        # services/tts/selection.py
    def voice_key(self, language_code: str) -> str: ...
    def is_available(self, language_code: str) -> bool: ...
    def provider_for(self, language_code: str) -> TTSProvider: ...  # raises VoiceUnavailable
```

`services/factory.py` builds `SpeechForLanguage` from the learner's `voice_choices`, `voice_for`,
`voice_unavailable_message`, a `PiperVoiceInstallation` and a `PiperTTSProvider` builder. The
existing `get_tts` dependency is **removed**; its three callers move to `get_speech_for_language`.
It is the only place Piper is named (Principle VI).

## 10. UI contract and E2E

| Surface | Contract | E2E (`frontend/e2e/`) |
|---|---|---|
| Settings | A "Practice language" radio group (Spanish, German) sits before "Voice". Selecting German lists only German voices, with German's `selected_voice` pre-selected. If that voice is not installed, the voice hint shows the plain message. One Save sends `target_language` and `tts_voice`. The level and correction warnings still render (spec Edge Cases). | `practice-language.spec.ts` (new); `settings.spec.ts` extended |
| Home | "Practising **German** · Change in Settings" is visible, and the link goes to `/settings` (FR-004) | `home.spec.ts` extended |
| Chat | The header shows the conversation's language as text, with no control. The helper label reads "English → German". The transcribe request carries `language=de` for a German conversation, even while Spanish is selected. A `VoiceUnavailableNotice` (`role="status"`) is shown and audio does not auto-play when the conversation's voice is not installed. | `chat.spec.ts` extended; `practice-language.spec.ts` |
| Past Chats | Each row shows its language name (FR-012) | `history.spec.ts` extended |
| Flashcards (list, decks, practice, analytics) | Every collection request carries `language=<practice language>`. A language switch never shows the other language's cached data (the query keys include the language). An audio failure shows the 503 `detail`. | `flashcards.spec.ts`, `flashcard-practice.spec.ts`, `flashcard-analytics.spec.ts` extended |

**New fixtures** (`frontend/e2e/fixtures.ts`):
- `mockPracticeLanguages` (both installed) and `mockPracticeLanguagesGermanVoiceMissing`;
- `mockGermanConversation`;
- `mockGermanVoices`.

Existing fixtures that use `target_language: 'Spanish'` are corrected to codes (`'es'`), with the
matching `*_name` fields.
