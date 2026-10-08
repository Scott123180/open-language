# API Contract: Language Switcher in the Header

**Feature**: 009-language-switcher-header

One endpoint gains two fields. One existing endpoint is used in a new way, unchanged. No endpoint is
added or removed.

## `GET /api/settings/practice-languages` (changed: two fields added)

Returns every catalogued practice language in catalogue order, as today.

```json
[
  {
    "language_id": "es",
    "display_name": "Spanish",
    "flag": "es",
    "has_activity": true,
    "is_default": true,
    "default_voice": "es_ES-davefx-medium",
    "selected_voice": "es_ES-davefx-medium",
    "is_voice_installed": true,
    "voice_unavailable_message": null
  },
  {
    "language_id": "it",
    "display_name": "Italian",
    "flag": "it",
    "has_activity": false,
    "is_default": false,
    "default_voice": "it_IT-paola-medium",
    "selected_voice": "it_IT-paola-medium",
    "is_voice_installed": true,
    "voice_unavailable_message": null
  }
]
```

| New field | Type | Contract |
|---|---|---|
| `flag` | string, non-empty | The language data's `flag`. Always present for a catalogued language. |
| `has_activity` | boolean | `true` when the learner has at least one conversation (roleplay or podcast episode) or one flashcard deck in this language. Does **not** consider the current practice language; the client adds that (research R3). |

Errors: unchanged (a storage failure is a 500, as for every settings read).

Tests (contract, `backend/tests/contract/`):
- every entry has a non-empty `flag` equal to the language data's value;
- `has_activity` is `false` for every language on an empty database;
- a conversation in `de` makes `de` `true` and leaves the others `false`;
- a podcast episode (a `conversations` row) in `it` makes `it` `true`;
- a flashcard deck in `de` with no conversation makes `de` `true`;
- the current practice language with no activity is `false`.

## `PUT /api/settings` (unchanged, new caller)

The header switcher sends only the language:

```json
{ "target_language": "de" }
```

Response: the full `SettingsResponse`, as today, with `target_language: "de"` and `tts_voice` set to
the voice remembered for German (or German's default voice). Other settings and every language's
remembered voice are unchanged. An unknown code is a 422, as today.

Test (contract): a `PUT` with only `target_language` after a German voice was chosen returns that
German voice in `tts_voice` and leaves `voice_choices` for Spanish untouched.

## Frontend type

`PracticeLanguageOption` in `frontend/src/services/api.ts` gains `flag: string` and
`has_activity: boolean`. `frontend/e2e/fixtures.ts` language mocks gain both fields.
