# Interface Contracts: Podcast Mode

**Feature**: [spec.md](../spec.md) | **Data model**: [data-model.md](../data-model.md) |
**Research**: [research.md](../research.md)

All paths are under `/api`. Unless a section says otherwise, the shapes of existing endpoints are
unchanged. Language values on the wire are catalogue codes. Display names travel only in fields
whose names end in `_name` or `label`.

Sections: **§1–§8 new podcast endpoints**, **§9 summary (new)**, **§10 settings (extended)**,
**§11 speech (extended)**, **§12 module interfaces**, **§13 UI and E2E**.

The shared errors are:
- `503 {"detail": <provider message>}` for any `LLMError` (existing handler);
- `503` for `VoiceUnavailable` (existing handler);
- `404 {"detail": "Episode not found"}`;
- `409 {"detail": <plain next step>}` for an action the turn state does not allow.

---

## 1. `GET /api/podcasts/catalog`

Everything the Podcasts and setup screens need, for the **current practice language**.

**200**

```json
{
  "language": "es",
  "language_name": "Spanish",
  "formats": [
    {"format_id": "one_host", "label": "One host", "host_count": 1, "is_learner_speaking": true, "description": "You and one host."},
    {"format_id": "panel", "label": "Panel", "host_count": 2, "is_learner_speaking": true, "description": "You and two hosts."},
    {"format_id": "listen", "label": "Listen", "host_count": 2, "is_learner_speaking": false, "description": "Two hosts talk; you listen."}
  ],
  "lengths": [
    {"length_id": "short", "label": "Short", "target_host_lines": 10, "is_default": false},
    {"length_id": "medium", "label": "Medium", "target_host_lines": 20, "is_default": true},
    {"length_id": "long", "label": "Long", "target_host_lines": 40, "is_default": false}
  ],
  "personalities": [
    {"personality_id": "enthusiast", "label": "Enthusiast", "description": "Excited about everything and quick to share."}
  ],
  "shows": [ShowDraft, "…"],
  "voices": {
    "installed_count": 2,
    "shared_voice_notice": null,
    "unavailable_message": null
  }
}
```

**`ShowDraft`** is used here, in §3 and §4, and in the body of §6:

```json
{
  "source": "ready_made",
  "show_id": "weekend-food-talk",
  "title": "Weekend Food Talk",
  "premise": "Two food lovers swap weekend cooking wins and disasters.",
  "topic": "food",
  "learner_role": "guest",
  "language": "es",
  "hosts": [
    {"slot": "lead", "name": "Lucía", "personality_id": "enthusiast", "voice_key": "es_AR-daniela-high", "show_role": "host", "angle": null},
    {"slot": "second", "name": "Marco", "personality_id": "dry_sceptic", "voice_key": "es_ES-davefx-medium", "show_role": "co_host", "angle": null}
  ]
}
```

| Guarantee | Test |
|---|---|
| Formats, lengths, personalities and shows come from the catalogues in order; there are ≥ 6 shows | contract |
| Every draft has two hosts, with different names and personalities, and different voices when `installed_count ≥ 2` | contract + unit (`HostCaster`) |
| Host names come from the language's name bank and match the voice's gender | unit |
| A ready-made show's default names are stable across calls for the same language | unit |
| `shared_voice_notice` is non-null exactly when `installed_count == 1`; `unavailable_message` exactly when it is 0 | integration with a fake `VoiceInstallation` |

## 2. `GET /api/podcasts/preferences` and `PUT /api/podcasts/preferences`

**200** (both):

```json
{"last_format": "one_host", "is_show_text_on": false, "interests": ["football", "cooking"], "learner_name": null}
```

**PUT body**: any subset of `is_show_text_on`, `interests` and `learner_name`. `learner_name: ""`
clears it. `last_format` is read-only, and only §6 writes it.

| Guarantee | Test |
|---|---|
| Interests are trimmed and de-duplicated case-insensitively. More than 10 items, or an item over 40 characters, gives a 422 that names the problem | contract |
| Values persist across a restart (a new session factory) | integration |
| Interests are never written except by this endpoint (FR-023: not inferred) | integration: a conversation and a saved word leave them unchanged |

## 3. `POST /api/podcasts/shows/generate` and `POST /api/podcasts/shows/surprise`

**Generate body**: `{"idea": "football tactics", "avoid_titles": ["Tiki-Taka Talk"]}`.
`avoid_titles` is optional and used by "Another version" (FR-021).

**Surprise body**: `{}`.

**200**: a `ShowDraft` with `source: "generated"` or `"surprise"` and `show_id: null`. Nothing is
stored.

**422** (generate only):

```json
{"detail": "That idea can't become a show here. Try a different topic, or press Surprise me.", "can_surprise": true}
```

- An empty idea, or one over 200 characters, is rejected before any model call.
- An unsuitable idea is declined by the model's `is_suitable: false` (FR-024).

| Guarantee | Test |
|---|---|
| A structured-output reply becomes a draft whose names and voices are cast by code, whatever names the model wrote | unit, with a scripted `StructuredLLMProvider` |
| `is_suitable: false` → 422 with `can_surprise`; the model's reason is logged, never returned | unit |
| Surprise me draws from interests in ≥ 60% of 300 seeded draws when interests exist, and never repeats one of the last 10 (topic, angle) pairs | unit (FR-022, FR-023) |
| Malformed model JSON → 503 with a plain retry message (as corrections do) | unit |

## 4. `POST /api/podcasts/hosts/shuffle`

**Body**: `{"language": "es", "slot": "second", "hosts": [HostDraft, HostDraft], "learner_name": "Sam"}`

**200**: a new `HostDraft` for `slot`. Its name and personality differ from the other host's and
from the replaced host's, and its name is not the learner's. Its voice differs from the other
host's when two or more voices are installed.

| Guarantee | Test |
|---|---|
| Three shuffles in a row never produce a name, personality or voice clash (US5 independent test) | unit, seeded |

## 5. `GET /api/podcasts/voice-sample?voice_key=…&name=…`

**200** `audio/wav`: the language's `sample_line` with the name, spoken in that voice, and cached
by `(voice_key, name)`.

**503** `VoiceUnavailable` when the voice is not installed. **422** for an unknown voice.

## 6. Episodes

### `POST /api/podcasts/episodes`: start an episode

**Body**:

```json
{"show": ShowDraft, "format": "panel", "length": "medium", "learner_name": "Sam"}
```

**201**: an `EpisodeResponse` (below). This call:
- creates the conversation, stamped with the current practice language;
- creates the episode, the participating hosts (One host stores only the lead), and
  `podcast_preferences.last_format = format`. It also saves `learner_name` when one is given.

**422**: the draft fails the checks in data-model §6, or `show.language` is not the current practice
language ("The practice language changed. Pick the show again.").

### `GET /api/podcasts/episodes`: Past Chats labels

**200**:

```json
[{"conversation_id": 57, "show_title": "Weekend Food Talk", "format": "panel", "format_label": "Panel", "host_names": ["Lucía", "Marco"], "language": "es", "language_name": "Spanish", "status": "active"}]
```

### `GET /api/podcasts/episodes/{conversation_id}`: `EpisodeResponse`

```json
{
  "conversation_id": 57,
  "status": "active",
  "language": "es",
  "language_name": "Spanish",
  "native_language_name": "English",
  "show": {"title": "Weekend Food Talk", "premise": "…", "topic": "food", "learner_role": "guest", "source": "ready_made", "show_id": "weekend-food-talk"},
  "format": "panel",
  "format_label": "Panel",
  "length": "medium",
  "target_host_lines": 20,
  "learner_name": "Sam",
  "hosts": [
    {"host_id": 11, "slot": "lead", "name": "Lucía", "personality_id": "enthusiast", "personality_label": "Enthusiast", "voice_key": "es_AR-daniela-high", "show_role": "host", "is_voice_available": true, "voice_unavailable_message": null}
  ],
  "shared_voice_notice": null,
  "turn": "hosts",
  "awaiting": "continue",
  "can_jump_in": true,
  "can_pass": false,
  "lines": [
    {"message_id": 901, "speaker": "host", "host_id": 11, "content": "¡Bienvenidos a …!", "intent": "open", "invites_learner": false, "is_revealed": false, "created_at": "2026-09-28T10:00:00Z"},
    {"message_id": 903, "speaker": "learner", "host_id": null, "content": "Hola …", "intent": null, "invites_learner": false, "is_revealed": true, "created_at": "…"}
  ]
}
```

| Guarantee | Test |
|---|---|
| `turn` and `awaiting` follow data-model §4 exactly | unit (policy) + integration |
| Hosts, names and voices are identical on every read, before and after a restart (FR-009, US1-6) | integration |
| `is_voice_available` is false with the host-specific message when the host's voice is missing; the voice is never changed (FR-031) | integration with a fake installation |
| `lines` are the conversation's messages in order; every host line has exactly one `host_id` | integration |

## 7. Line-producing actions (SSE, `text/event-stream`)

| Endpoint | Body | Allowed when | 409 detail otherwise |
|---|---|---|---|
| `POST /api/podcasts/episodes/{id}/next` | — | `turn == "hosts"` | "It's your turn. Reply, pass or end the episode." / "This episode has finished." |
| `POST /api/podcasts/episodes/{id}/message` | `{"content", "input_source", "transcription_confidence"}`, the same as `/chat/{id}/message` | data-model §4 | "This is a listening episode. Start the show in One host or Panel to speak." |
| `POST /api/podcasts/episodes/{id}/pass` | — | `turn == "learner"` and Panel | "You can pass only when it's your turn in a Panel." |
| `POST /api/podcasts/episodes/{id}/end` | — | not finished | "This episode has finished." |

Any of them while another line of the same episode is in progress returns **409 "A line is already
on its way."** (research R12).

**Frames**, in order:

```text
data: {"event": "user_message_saved", "message_id": 903}                     # /message only
data: {"event": "feedback", "message_id": 903, "awaiting_retry": false, "notes": [...]}   # /message, as chat
data: {"event": "line", "line": <line object as in §6>, "turn": "learner", "awaiting": null}
data: {"done": true, "turn": "learner", "awaiting": null}
```

- A provider failure sends `data: {"error": "<LLMError.user_message>"}` and stores nothing. Calling
  `/next` again retries the same line (edge case "provider fails mid-episode").
- A Strict correction pause sends `done` with `turn: "learner"` and no `line`, as the chat does.
- `/end` sends the sign-off `line`, then `done` with `turn: "finished"`. The conversation is
  completed and the podcast session ended.
- In Listen, a `sign_off` line reached through length also finishes the episode.
- `/pass` marks the invitation passed, then produces the next line.
- `/message` in One host or Panel produces the first host response straight after the learner line
  (FR-016). Later lines wait for `/next`.
- The line's audio is scheduled in the host's voice as soon as the line is stored, so
  `GET /api/audio/tts/{message_id}` is usually a cache hit (§11).

| Guarantee | Test |
|---|---|
| The stored and streamed text never contains another participant's label (FR-012) | unit (sanitiser) + integration with a scripted writer that leaks labels |
| A trimmed line ends the podcast session, so the next line rebuilds from storage | integration with `RecordingSessionProvider` |
| The cue history re-renders byte-for-byte on rebuild | unit (`render_cue` over stored facts) |
| A level change between two lines rebuilds the session and appends the new level's rules | integration |
| Concurrent `/next` requests → exactly one line, one 409 | integration |
| Corrections, pause and retry behave as in chat | integration, reusing the corrections fixtures |

## 8. Other episode endpoints

- **`POST /api/podcasts/episodes/{id}/session`** → `202 {"status": "warming" | "live"}`. The same
  as `/chat/{id}/session`, for `SessionKind.PODCAST`.
- **`POST /api/podcasts/episodes/{id}/suggestions`** → `{"suggestions": [...]}`. This is the
  roleplay suggestion prompt over a transcript labelled with host names and the learner label, with
  the level's learner-text rules. It returns 409 in Listen.
- **`POST /api/podcasts/episodes/{id}/lines/{message_id}/reveal`** → `204`. It sets `is_revealed`
  and is idempotent. It returns 404 for a message that is not a host line of this episode.

## 9. `GET /api/conversations/{conversation_id}/summary` (new, roleplay and podcasts)

**200**:

```json
{
  "status": "ready",
  "conversation_id": 57,
  "up_to_message_id": 931,
  "conversation_language": "de",
  "conversation_language_name": "German",
  "native_language_name": "English",
  "points": [
    {"conversation_language": "Lena findet die Markthalle toll.", "english": "Lena loves the market hall."},
    {"conversation_language": "Jonas sagt: Tapas sind zu teuer.", "english": "Jonas says tapas are too expensive."}
  ]
}
```

or `{"status": "too_early", "message": "There's nothing to summarise yet. Reply to the opening line first."}`

- `404` for an unknown conversation. `503` (`LLMError`) with the provider's message, and a retry
  in the UI.
- It uses the conversation's language, never the current setting (edge case).

| Guarantee | Test |
|---|---|
| 1–5 points; each has both versions | unit (parser rejects 0 or > 5 → 503 retry message) |
| A cache hit when the last message id and the level are unchanged; a regeneration after a new line or a level change | integration |
| Transcript labels use host names in episodes, "Learner" and "Partner" in roleplay | unit (`SpeakerNames`) |
| Transcripts over the chunk budget are folded; no single prompt exceeds the budget | unit |
| Reading a summary adds no message, and does not touch the conversation's session (FR-041) | integration: message count and `engine.is_live` unchanged |

## 10. `GET /api/settings` and `PUT /api/settings` (extended)

- `SettingsResponse` gains `summary_language: "conversation" | "native"`.
- `UpdateSettingsRequest` gains `summary_language` with pattern `^(conversation|native)$`.

Every other field is unchanged.

## 11. `GET /api/audio/tts/{message_id}` (extended)

A host line is spoken in **its host's voice**:
- the router asks the injected `MessageVoiceLookup` for the message's voice;
- `None` keeps today's path, the conversation's language voice;
- a voice key goes through `SpeechForLanguage.provider_for_voice(language, voice_key)`.

A missing host voice gives a 503 with that host's message. There is **never** another voice
(FR-031).

| Guarantee | Test |
|---|---|
| Roleplay messages are unaffected (the lookup returns `None`) | the existing audio tests pass unchanged |
| Two hosts' lines are synthesised with their two voices | integration with `RecordingTtsBuilder` |
| A voice that does not speak the conversation's language is refused | unit (`provider_for_voice`) |

## 12. Module interfaces

### `app.podcasts` (package root: the only import surface)

`router`, `PODCAST_SCENARIO_ID`, `PodcastMessageVoices` (implements `MessageVoiceLookup`) and
`PodcastSpeakerNames` (implements `SpeakerNames`). The last two are constructed only in
`services/factory.py`.

Internal, not importable from outside:
- `catalog`, `prompts`;
- `services/`: `turn_policy`, `cues`, `sanitiser`, `casting`, `generator`, `surprise`, `storage`
  (ABC), `sqlite_storage` and `episode_lock`.

### `app.conversation_summary`

`router` and `SpeakerNames` (ABC: `names_for(conversation_id) -> Mapping[int, str] | None`).
Internal: `services/summariser` (fold, parse, cache), `services/storage` and `prompts`.

### `app.conversation_turns` (moved from `routers/chat.py`, research R11)

`sse`, `EngineTurn`, `SavedReply`, `relay_engine_reply`, `LearnerMessageRequest` (formerly
`ChatMessageRequest`, re-exported under its old name for the chat router), `save_learner_message`,
`Corrections` and `schedule_speech`.

### Additions to existing modules

| Module | Addition |
|---|---|
| `services/conversation/session.py` | `SessionKind.PODCAST` |
| `services/tts/base.py` | `MessageVoiceLookup` ABC (one method) |
| `services/tts/selection.py` | `SpeechForLanguage.provider_for_voice(language, voice_key, unavailable_message)` |
| `practice_languages` | `PracticeLanguage.host_names`, `.guest_labels` and `.sample_line`. The package gains `host_names_for(code, gender)`, `guest_labels_for(code)` and `voice_sample_line(code, name)` |
| `services/factory.py` | `get_podcast_storage`, `get_message_voices`, `get_speaker_names`, `get_episode_locks` and `get_recent_surprises` |
| `database.py` | registers the new models; adds one `_ADDITIVE_COLUMNS` entry |
| `main.py` | includes the podcasts and summary routers |

## 13. UI and E2E contracts

| Screen | Primary action | Secondary | Accessibility |
|---|---|---|---|
| Home | Start a scenario (unchanged) | New "Podcasts" nav pill | Link text |
| Podcasts (`/podcasts`) | Choose a show card | Generate, Surprise me, and an "Your interests" disclosure | Cards are buttons with the title as the accessible name; the generator input is labelled; errors use `role="alert"` |
| Setup (`/podcasts/setup`) | **Start episode** | Format and length radios; per host: shuffle, a personality select and ▶ sample; Another version (generated only) | `fieldset`/`legend` for the radios; the shared-voice notice is `role="status"` |
| Episode (`/podcasts/episodes/:id`) | **Continue** at the hosts' turn; **Send / record** at the learner's turn | Jump in, Pass, End episode, Summary, Show text (Listen) | The turn banner is `role="status"` ("Your turn" / "Lucía is speaking"); a hidden line is a button labelled "Show Lucía's line"; the controls' visible labels match their accessible names |
| Chat | Unchanged | New Summary button in the header | The summary panel is a labelled region; the language switch is a two-option radio group |

**E2E specs** (`frontend/e2e/`), with all API calls mocked through `page.route()`:
- `podcasts.spec.ts` (new): list, interests, generate, decline, another version, Surprise me, and
  setup (format, length, shuffle, personality, shared-voice notice).
- `podcast-episode.spec.ts` (new):
  - One host: opening, reply, End.
  - Panel: Continue, turn banner, Jump in, Pass, and naming a host.
  - Listen: hidden lines, reveal, Show text remembered, Continue to sign-off.
  - Provider error with retry, and a missing host voice.
- `conversation-summary.spec.ts` (new):
  - roleplay and podcast summaries, and the too-early message;
  - the language switch, remembered across conversations;
  - closing the panel leaves the transcript untouched.
- `home.spec.ts` and `history.spec.ts` are extended (the nav pill, and podcast rows linking to the
  episode screen).
- `chat.spec.ts` is extended (the Summary button is present and changes nothing else).
- `fixtures.ts`: `showDraftFixture`, `episodeFixture(format)`, `lineFrame()` and `summaryFixture`.
