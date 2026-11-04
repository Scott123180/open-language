# Contracts: Configurable Podcast Shows

**Feature**: `011-configurable-podcast-shows` | **Data model**: [../data-model.md](../data-model.md)

Every HTTP change is additive. A request without the new fields behaves like this feature's
defaults: a new episode gets Balanced · Medium · Sometimes and the show's role. A client that
ignores the new response fields and SSE events keeps working. Error bodies are FastAPI's
`{"detail": "…"}`, with a plain sentence that says what to do (Principle IV).

---

## 1. `GET /api/podcasts/catalog` (extended)

The response gains `episode_options`, so the setup renders the settings from the server's
catalogue:

```json
{
  "episode_options": {
    "styles": [
      {"style_id": "conversation", "label": "Conversation", "description": "Lots of back-and-forth.", "is_default": false},
      {"style_id": "balanced", "label": "Balanced", "description": "Some talk, some explaining.", "is_default": true},
      {"style_id": "presented", "label": "Presented", "description": "The hosts mostly explain and tell stories, like a radio show.", "is_default": false}
    ],
    "line_lengths": [{"line_length_id": "short", "label": "Short", "is_default": false}, …],
    "invite_frequencies": [{"invite_frequency_id": "often", "label": "Often", "is_default": false}, …],
    "learner_roles": [{"learner_role": "guest", "label": "Guest"}, {"learner_role": "co_host", "label": "Co-host"}, {"learner_role": "caller", "label": "Caller"}],
    "today_subject_max_length": 120
  }
}
```

The `formats` entries gain `has_jump_in` and `has_pass` (data-model §1.5).

## 2. `GET / PUT /api/podcasts/preferences` (extended)

`PreferencesResponse` gains three read-only fields:
- `last_style`;
- `last_line_length`;
- `last_invite_frequency`.

`PUT` does not accept them; they are written by a one-off start (FR-013), as `last_format` is.

---

## 3. `POST /api/podcasts/episodes` (extended)

```json
{
  "show": { …ShowDraft… },
  "format": "panel",
  "length": "medium",
  "learner_name": "Ana",
  "kind": "series",
  "settings": {
    "style": "presented",
    "line_length": "long",
    "invite_frequency": "rarely",
    "learner_role": "guest",
    "today_subject": "why do we yawn"
  },
  "from_now_on": ["style"],
  "guest": {"slot": "second", "name": "Marco", "personality_id": "expert", "voice_key": "es_ES-davefx-medium", "show_role": "co_host"}
}
```

| Field | Default when absent | Rule |
|---|---|---|
| `settings` | Defaults with the show's role | Data-model §5.1. Every field of `settings` is optional, and a missing one takes its default |
| `from_now_on` | `[]` | Series episodes after the first only (§5.2) |
| `guest` | `null` | Series episodes after the first only (§5.2) |

| Status | When |
|---|---|
| 201 | `EpisodeResponse` (§5) |
| 409 | 010's stale series hosts |
| 422 | Data-model §5.1 and §5.2 messages; 007 and 010 draft refusals |
| 503 | `SubjectCheck` could not reach the selected provider (only when `today_subject` is set) |

Order of work (each step stops the start on failure):
1. schema and catalogue checks;
2. `SeriesService.prepare` (010 checks, guest checks, `from_now_on`);
3. `SubjectCheck`, only with a subject;
4. `create_episode` in one transaction: conversation, episode, hosts, settings row, series link,
   series settings upsert;
5. preferences.

---

## 4. Line-producing endpoints: new SSE events

`POST /episodes/{id}/next`, `/message`, `/pass` and `/end` keep their bodies and status codes. A host
line's frames become:

```text
data: {"event": "line_started", "stream_id": "b3f1…", "host_id": 12}
data: {"event": "line_part", "stream_id": "b3f1…", "index": 0, "text": "Hola a todos.", "audio_url": "/api/podcasts/episodes/41/parts/b3f1…/0"}
data: {"event": "line_part", "stream_id": "b3f1…", "index": 1, "text": "Hoy hablamos de…", "audio_url": "/api/podcasts/episodes/41/parts/b3f1…/1"}
data: {"event": "line", "line": {…EpisodeLine…}, "turn": "learner", "awaiting": null}
data: {"done": true, "turn": "learner", "awaiting": null, "can_jump_in": false, "can_pass": false}
```

- `audio_url` is `null` when the host's voice is not installed. The line stays text, as 007 FR-031.
- The `line` frame's `content` is exactly the parts' texts joined by single spaces.
- An error after any `line_part` is `{"error": "The host lost their words. Press Retry.", "stream_id": "b3f1…"}`.
  The line is not stored, and the client drops the arriving line and stops its audio. An error
  before any part is 007's `{"error": …}`.
- `can_pass` now comes from the format's `has_pass`, and `can_jump_in` is true at One host's
  Continue (research R15).
- **No address tag ever reaches a frame** (research R19). `line_part.text`, the `line` frame's
  `content` and `GET /episodes/{id}` lines are tag-free. The `line` frame's `turn` is `learner`
  whenever the stored line invites, including a configured line that asked the learner something on
  a `none` cue. The frontend needs no change for this: it already follows `turn` and `awaiting`.
- `EpisodeLine.invites_learner` keeps its meaning: the learner had the turn after this line.

### `GET /api/podcasts/episodes/{conversation_id}/parts/{stream_id}/{index}` (new)

| Status | Body |
|---|---|
| 200 | `audio/wav`, once that part is synthesised (waits up to 30 s) |
| 404 | "That part of the line isn't there any more." (unknown, expired, or another episode's stream) |
| 503 | The voice became unavailable: 007's host voice message |
| 504 | "The line's audio took too long. Press Replay when the line has arrived." |

`GET /api/audio/tts/{message_id}` is unchanged. A streamed line's full WAV is cached when the line is
stored, so Replay and Slower return at once.

---

## 5. `EpisodeResponse` (extended)

```json
{
  "settings": {
    "style": "presented", "style_label": "Presented",
    "line_length": "long", "line_length_label": "Long",
    "invite_frequency": "rarely", "invite_frequency_label": "Rarely",
    "learner_role": "guest", "today_subject": "why do we yawn"
  },
  "hosts": [{ …EpisodeHost…, "is_guest": true }],
  "away_host_name": "Clara"
}
```

- `settings` is `null` for a pre-feature episode.
- `is_guest` is false for every host outside a guest episode.
- `away_host_name` is `null` unless a guest replaces a regular host.

The episode header shows "Guest: Marco" and "Clara is away" from these fields.

---

## 6. `GET /api/podcasts/series/{series_id}` (extended)

```json
{
  "usual_settings": {"format": "one_host", "length": "medium", "style": "balanced", "line_length": "medium", "invite_frequency": "sometimes", "learner_role": "guest"},
  "is_standard": true,
  "second_role_personality_id": "expert"
}
```

- `usual_settings` is the series' row, or the show's standard settings.
- `is_standard` decides whether **Use the show's standard settings** is shown.
- `second_role_personality_id` is the show's second personality, used for the automatic expert guest
  (FR-024a).

`SeriesHostModel` gains `has_taken_part` (true once the host has been in a series episode), so a
host about to join a One host series turned Panel reads "New to the show".

## 7. `DELETE /api/podcasts/series/{series_id}/settings` (new)

The settings reset (FR-019); the client shows `ConfirmDialog` first.

| Status | Body |
|---|---|
| 200 | `SeriesDetailResponse` with standard `usual_settings` |
| 404 | 010's "That series isn't there any more. Open the show again." |
| 422 | 010's `LANGUAGE_CHANGED`, when the series is not in the current language |

Past episodes, the episode count, the hosts and the memory are unchanged.

## 8. `POST /api/podcasts/series/{series_id}/guest` (new)

```json
{"language": "es", "slot": "second", "format": "panel", "personality_id": "expert", "learner_name": "Ana", "avoid_names": ["Marco"]}
```

- `personality_id` is optional. Without it the server uses the show's second personality when the
  slot is the second slot of a One host series, and otherwise a random free one.
- `avoid_names` makes **Another guest** draw a new name.

| Status | Body |
|---|---|
| 200 | `HostDraftModel`, the cast guest (research R10) |
| 404 | Series not found |
| 422 | Unknown slot or personality; a personality the other present host has ("Hugo already has that personality. Pick another one."); the slot not used by `format` |

Nothing is stored. The guest becomes part of an episode only through `POST /episodes`.

## 8a. `POST /api/podcasts/subject-suggestions` (new, research R20)

Served by `discovery_routes.py`, beside Find a new show.

```json
{"show": {"title": "Big Little Questions", "premise": "Everyday curiosities, from why toast lands butter-side down onwards.", "topic": "everyday curiosities"}, "series_id": 1, "avoid": ["why do we yawn"]}
```

- `show` is required: the title, premise and topic of the show on the setup screen, as in a
  `ShowDraft`.
- `series_id` is optional. With it, the series' covered topics are excluded.
- `avoid` is optional: the subjects already shown on this setup (at most 10).
- The practice language and the learner's interests come from the app settings and podcast
  preferences, as for Find a new show.

| Status | Body |
|---|---|
| 200 | `{"subjects": ["why coffee wakes you up slowly", "why bread goes stale", "why cats knock things over"]}`: 0 to 3 subjects in the learner's own language, each ≤ 120 characters, none equal to a covered or avoided subject |
| 404 | `series_id` unknown, or a series of another language: 010's "That series isn't there any more. Open the show again." |
| 422 | `avoid` too long (data-model §5.4) |
| 503 | The provider's message (Principle VI, no fallback) |

An empty `subjects` list is a 200. The UI says "No new subjects came back. Type one, or start
without one." Nothing is stored.

---

## 9. Prompts (internal contract, unit-tested)

| Piece | Legacy (pre-feature episode) | Configured |
|---|---|---|
| Level block | `with_partner_speech_rules` | `with_sentence_rules` (no reply cap) |
| Line length | "Keep each line to a few sentences" | "Each host line has {min} to {max} sentences…" in the line rules, plus the cue's brief or full phrase by intent (research R22) |
| Question rule | — | "When {label} asks a question, answer it first; never answer only with a question." |
| Asking rule | — | "Only ask {label} something when the producer note says so." |
| Closing question | — | "A closing question to {label} comes after the line's sentences and is not one of them." |
| No re-asking | — | "Never ask {label} something they have already answered in this episode." |
| One subject | — | "Every episode is about one subject, named in the opening. Stay on it until the wrap-up." |
| Address tag | — | "End every line with who it is for, in square brackets: [@{learner}], [@{other host}], or [@all] when it is for no one in particular. The brackets are never read aloud." (the last line rule; One host offers the learner and all) |
| Cue closing by `Ask` | Inviting: "End by asking {label} a question."; otherwise none | `required`: "Then end by asking {label} one question."; `allowed`: "If it fits, then end by asking {label} one question; if not, ask {label} nothing."; `none`: "Don't ask {label} anything this time." |
| Opening | 007 / 010 wording | Adds the subject: "…and introduce today's subject." or "…and name today's one subject: one concrete question or thing within the show's topic." (+ "not in the covered list" in a series) |
| Wrap-up | "Start wrapping up the topic, in character." + invite | "Start wrapping up: tell {label} the show is nearly over, and sum up today's subject in one sentence." + "Then ask {label} for one last thought on it." (Listen: no ask) |
| Sign-off | "Close the show: thank {label} and say goodbye." | "React briefly to the last line, then close the show: thank {label} and say goodbye." |
| Speaking styles | `speaking_style` | `configured_speaking_style` when set (expert, curious interviewer; research R22) |
| History | Assistant turns are the stored text | Stored text + " [@Name]" or " [@all]", rebuilt from `addressee` |
| One host covered role | — | "This show usually has a second host, the {Label}: …" |
| Today's subject | — | In the show section |
| Guest and away | — | In the series section and `open`/`greet` cues |
| Missed marks | — | `[Name was away for this]` and one rule, only when present |

Golden tests:
- 007's one-off golden and 010's series prompt tests run against `LegacyTalk` and stay unchanged;
- a new golden pins a configured one-off with defaults;
- a new golden pins a configured series guest episode.

Bounds: a configured standing prompt with a full series section is ≤ 900 tokens; a cue is ≤ 60
tokens.

`app.conversation_levels` gains `with_sentence_rules` in its package root's `__all__`.

---

## 10. Module interfaces

### `app.podcasts` (package root: unchanged)

### Inside `app.podcasts`

| Module | Change |
|---|---|
| `catalog.py` | Style, line length and invite frequency catalogues; `PodcastFormat.has_pass`; constants |
| `models.py` | `PodcastEpisodeSettings`, `PodcastSeriesSettings`; three `PodcastPreferences` columns |
| `schemas.py` | `EpisodeSettingsModel`, `from_now_on`, `guest`, `EpisodeOptions`, `GuestRequest`, response fields |
| `prompts.py` | Configured sections and cue text through `HostTalk`; series guest, away and missed rendering; subject-check prompt and schema |
| `responses.py` | `episode_options`, settings, guest fields, `usual_settings` |
| `routes.py` | Start passes settings, guest and `from_now_on`; part-audio route; `_remember_start` writes the last-used settings |
| `series_routes.py` | Settings reset, guest casting |
| `services/host_talk.py` (new) | `HostTalk`, `LegacyTalk`, `ConfiguredTalk`, `host_talk_for` |
| `services/episode_settings.py` (new) | `EpisodeSettings` |
| `services/series_settings.py` (new) | `SeriesSettings` |
| `services/subject_check.py` (new) | `SubjectCheck`, `SubjectDeclined` |
| `services/subject_suggestions.py` (new) | `SubjectSuggester`, `SubjectRequest` (research R20) |
| `services/line_address.py` (new) | `LineAddress`, `LineAddressResult` (research R19) |
| `discovery_routes.py` | `POST /subject-suggestions` |
| `services/sentences.py` (new) | `SentenceSplitter` |
| `services/line_writer.py` (new) | `LineWriter`: streams, splits, sanitises, retries; yields parts |
| `services/spoken_parts.py` (new) | `SpokenParts`, `LinePart`, WAV assembly |
| `services/turn_policy.py` | Reads `state.talk` for invitations and discussion intents |
| `services/episode_turns.py` | `_line_events` relays parts from `LineWriter`; speech through `SpokenParts` |
| `services/episodes.py` | `LoadedEpisode.talk`, settings, guest facts |
| `services/cues.py` | Cue rendering through the episode's talk |
| `services/series.py` | Settings, scopes, guests, snapshot marks, first appearances |
| `services/casting.py` | `HostCaster.cast_guest` |
| `services/sanitiser.py` | `StreamingSanitiser` |
| `services/series_snapshot.py` | `RememberedLine`, guest and away fields, both JSON forms |
| `services/storage.py`, `sqlite_storage.py` | Settings row, settings upsert in `create_episode`, preference columns |
| `services/series_storage.py`, `sqlite_series_storage.py` | `hosts_present`, `reset_settings`, settings on `SeriesRecord`, `RememberedPoint.conversation_id` |

### Outside `app.podcasts`

| Module | Change |
|---|---|
| `app/conversation_levels/rules.py`, `__init__.py` | `with_sentence_rules` (new, pure) |
| `app/services/conversation/pool.py`, `engine.py` | `run_turn_live` / `stream_live` (new) |
| `app/conversation_turns/streaming.py` (new), `__init__.py` | `iterate_in_thread` |
| `app/services/factory.py` | `get_spoken_parts` (process-wide), `get_subject_check`, `get_subject_suggester` |
| `app/database.py` | Five `_ADDITIVE_COLUMNS` entries (three preferences, two host lines) |
| **Not modified** | `prompts/templates.py`, `routers/chat.py`, `routers/audio.py`, `conversation_summary/*`, `services/llm/*`, `services/tts/*`, `practice_languages/*`, `language_data/*`, `language_kit/*` |

`test_module_boundaries.py` adds `spoken_parts`, `subject_check` and `subject_suggestions` to the
modules only the factory imports from outside `app.podcasts`.

---

## 11. UI and E2E contracts

| Element | Role and name | Notes |
|---|---|---|
| Episode settings toggle | `button`, `aria-expanded`, name "Episode settings: Balanced · Medium lines · Asked sometimes" | Closed by default |
| Style, Host lines, How often you're asked, Your role | `radiogroup` (fieldset + legend), one per setting | The last two are absent in Listen |
| Today's subject | `textbox` "Today's subject (optional)", `maxlength=120`, live character count | |
| Suggest subjects | Secondary `button` **Suggest subjects** beside the field; while waiting, "Finding subjects…" and `aria-busy` | Pressing again sends the shown subjects as `avoid` |
| Suggested subjects | A `list` in a polite live region; each item is a `button` naming the subject ("Use: why bread goes stale") | Choosing fills the textbox and moves focus to it; an empty reply or a 503 shows its message in the region |
| Scope question | `alertdialog` "Change for which episodes?", with buttons **Just this episode** and **This and later episodes** | Escape reverts |
| Scope mark | Text in the legend: "this episode" / "from now on" | |
| Standard settings | Button **Use the show's standard settings** → `ConfirmDialog` | Only when not standard |
| Invite a guest | Button **Invite a guest…** on each series host card → `GuestDialog` (personality radio group, **Invite**) | |
| Guest card | "Guest · this episode", **Another guest**, **Remove guest**; the regular card reads "Away this episode" | |
| Arriving line | The host line renders its parts as they come, with `aria-busy="true"`; Replay and Slower are absent until `line` | Listen with Show text off: hidden as today |

New E2E specs:
- `podcast-episode-settings.spec.ts`: the disclosure, the summary, defaults, last-used, Listen,
  subject decline, Suggest subjects (choose, again with `avoid`, empty, 503), one primary action;
- `podcast-series-settings.spec.ts`: scopes, marks, the next setup, the standard-settings reset,
  SC-007 in three choices;
- `podcast-guests.spec.ts`: invite, another, remove, the away label, the episode header.

`podcast-episode.spec.ts` gains:
- streamed parts playing in order;
- Replay after `line`;
- an error mid-line;
- Jump in for One host.

Fixtures (`frontend/e2e/fixtures.ts`) gain:
- `episodeOptions`;
- `subjectSuggestions` (three subjects) and `noSubjectSuggestions`;
- `seriesWithSettings`;
- `guestDraft`;
- `streamedLineFrames(parts)`, which builds the §4 SSE body.
