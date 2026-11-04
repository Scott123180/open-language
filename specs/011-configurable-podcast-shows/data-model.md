# Data Model: Configurable Podcast Shows

**Feature**: `011-configurable-podcast-shows` | **Date**: 2026-10-18 | **Research**: [research.md](research.md)

Every change is additive:
- two new tables;
- three new columns on `podcast_preferences`;
- two new nullable columns on `podcast_host_lines` (added 2026-11-03, research R19);
- new optional keys in the series snapshot JSON.

No existing row is rewritten. Episodes and series from before this feature keep working through the
"no row" defaults below (FR-025, SC-010).

---

## 1. Catalogue values (`app/podcasts/catalog.py`)

Behaviour reads descriptor fields, never ids (007's rule). Each catalogue is a `MappingProxyType` in
display order, with a `DEFAULT_…` constant.

### 1.1 `EpisodeStyle`

| id | label | description (learner-facing) | weights: react / explain / story |
|---|---|---|---|
| `conversation` | Conversation | Lots of back-and-forth. | 0.90 / 0.07 / 0.03 |
| `balanced` *(default)* | Balanced | Some talk, some explaining. | 0.55 / 0.30 / 0.15 |
| `presented` | Presented | The hosts mostly explain and tell stories, like a radio show. | 0.35 / 0.40 / 0.25 |

Validation: the weights are positive and sum to 1 (`__post_init__`).

### 1.2 `HostLineLength`

| id | label | min_sentences | max_sentences | brief_phrase | full_phrase |
|---|---|---|---|---|---|
| `short` | Short | 1 | 2 | in one or two sentences | in two sentences |
| `medium` *(default)* | Medium | 3 | 5 | in three sentences | in four or five sentences |
| `long` | Long | 5 | 8 | in five or six sentences | in six to eight sentences |

`range_phrase` ("three to five sentences") is built from min and max for the standing line rule.
`BRIEF_INTENTS = ("greet", "react", "wrap_up", "sign_off")` take `brief_phrase`; every other intent
takes `full_phrase` (research R22). Validation: 1 ≤ min ≤ max.

### 1.3 `InviteFrequency`

| id | label | hazards (1st, 2nd, 3rd host line since the learner) |
|---|---|---|
| `often` | Often | 1.0, 1.0, 1.0 |
| `sometimes` *(default)* | Sometimes | 0.35, 0.45, 0.55 |
| `rarely` | Rarely | 0.0, 0.05, 0.10 |

`INVITE_DEADLINE = 4`: the 4th host line in a row always invites (FR-003). Validation: each hazard
is in [0, 1].

### 1.4 Other constants

| Name | Value | Use |
|---|---|---|
| `TODAY_SUBJECT_MAX_LENGTH` | 120 | FR-010 |
| `SERIES_SETTING_NAMES` | `("format", "length", "style", "line_length", "invite_frequency", "learner_role")` | What `from_now_on` may name (§5.2) |
| `ANSWER_INTENTS` | `("answer", "follow_up")` | Policy priority (§4) |
| `DISCUSSION_INTENTS` | `("react", "explain", "story")` | Style draw (§4) |
| `QUESTION_MARK` | `"?"` | Question detection (research R4) |
| `ASKS` | `("required", "allowed", "none")` | A cue's `Ask` level (research R19) |
| `ADDRESSEES` | `("learner", "lead", "second")` | Stored addressees; `None` means no one in particular |
| `ADDRESS_ALL` | `"all"` | The tag for no one in particular |
| `ADDRESS_TAG_MAX_LENGTH` | 60 | Longest text inside an address tag |
| `BRIEF_INTENTS` | `("greet", "react", "wrap_up", "sign_off")` | Intents that take `brief_phrase` (R22) |
| `SUBJECT_SUGGESTIONS` | 3 | Most subjects one Suggest subjects press returns (R20) |
| `SUBJECT_AVOID_MAX` | 10 | Most already-shown subjects a request may send |
| `MIN_SENTENCE_CHARACTERS` | 12 | `SentenceSplitter` (research R13) |
| `PART_WAIT_SECONDS` | 30 | Part audio endpoint |
| `PART_TTL_SECONDS` | 600 | `SpokenParts` expiry |

### 1.5 `PodcastFormat` (changed)

The format gains `has_pass: bool`. One host's `has_jump_in` changes to true (research R15).

| id | has_jump_in | has_pass |
|---|---|---|
| `one_host` | **true** (was false) | false |
| `panel` | true | **true** |
| `listen` | false | false |

### 1.6 `Personality` (changed)

`Personality` gains `configured_speaking_style: str | None = None`. It is used by `ConfiguredTalk`
only, and `None` means the personality's `speaking_style` (research R22). It is set for `expert` and
`curious_interviewer` with the R22 wording.

---

## 2. Tables (`app/podcasts/models.py`)

### 2.1 `podcast_episode_settings` (new)

How an episode sounds, frozen at Start (FR-012). Episodes with no row are pre-feature episodes, and
they use `LegacyTalk` (research R1).

| Column | Type | Rule |
|---|---|---|
| `conversation_id` | Integer, PK, FK `podcast_episodes.conversation_id` ON DELETE CASCADE | One row per episode |
| `style` | String(14), not null | An `EpisodeStyle` id |
| `line_length` | String(8), not null | A `HostLineLength` id |
| `invite_frequency` | String(10), not null | An `InviteFrequency` id; stored but ignored in Listen |
| `today_subject` | String(120), null | Trimmed, newlines folded; null when not given |
| `covered_personality` | String(30), null | One host only: the absent second host's personality (research R6) |

**Your role** is `podcast_episodes.learner_role`, as today. It is now filled from the episode
settings rather than copied from the show.

### 2.2 `podcast_series_settings` (new)

A series' usual settings (FR-014). A series with no row has the show's standard settings (§3.3).

| Column | Type | Rule |
|---|---|---|
| `series_id` | Integer, PK, FK `podcast_series.id` ON DELETE CASCADE | One row per series |
| `format` | String(12), not null | A `PodcastFormat` id |
| `length` | String(8), not null | An `EpisodeLength` id |
| `style` | String(14), not null | |
| `line_length` | String(8), not null | |
| `invite_frequency` | String(10), not null | |
| `learner_role` | String(12), not null | One of `LEARNER_ROLES` |
| `updated_at` | DateTime(tz), not null | |

- Written by a series' first episode (insert).
- Written by a later episode with a non-empty `from_now_on` (upsert of the named fields), in the same
  transaction as the episode.
- Deleted by the settings reset (FR-019).
- `podcast_series` reset (010) cascades to it.

### 2.3 `podcast_preferences` (three additive columns)

Added through `_ADDITIVE_COLUMNS` in `app/database.py`:

| Column | Definition |
|---|---|
| `last_style` | `VARCHAR(14) NOT NULL DEFAULT 'balanced'` |
| `last_line_length` | `VARCHAR(8) NOT NULL DEFAULT 'medium'` |
| `last_invite_frequency` | `VARCHAR(10) NOT NULL DEFAULT 'sometimes'` |

Written by a one-off start only (FR-013).

### 2.4 Unchanged tables, new values

- `podcast_host_lines.intent` (String(10)) takes the new values `react`, `explain`, `story`,
  `answer` and `follow_up` in configured episodes. Legacy episodes keep `discuss`.

### 2.4a `podcast_host_lines` (two additive columns, research R19)

Added through `_ADDITIVE_COLUMNS` in `app/database.py`. Both are NULL on every pre-feature line and
on every line of a legacy episode.

| Column | Definition | Rule |
|---|---|---|
| `ask` | `VARCHAR(8)` NULL | The cue's `Ask`: `required`, `allowed` or `none`. NULL reads as `required` when `invites_learner` is true, else `none` |
| `addressee` | `VARCHAR(8)` NULL | `learner`, `lead` or `second`; NULL means no one in particular |

`invites_learner` keeps its meaning, "the learner has the turn after this line". In configured
episodes it is now `talk.invitation(ask, addressee)`, written once with the line.
- `podcast_hosts` holds a guest like any host. Its row is in the guest's slot; the episode's snapshot
  says which slot is a guest (§2.5).

### 2.5 Series snapshot JSON (`podcast_series_episodes.snapshot`, new optional keys)

```text
{
  "episode_number": 6,
  "topics_covered": ["bostezos", {"text": "las tostadas", "missed_by": ["second"]}],
  "about_learner": ["Ana tiene un gato.", …],
  "new_host_slots": [],
  "guest_slot": "second",          // new, optional: absent or null when there is no guest
  "away_host_name": "Clara"        // new, optional: the regular host the guest replaces
}
```

- A point is a plain string, as in 010, or an object `{text, missed_by}` when one or more of the
  episode's regular hosts missed the episode the point came from (research R11).
- `SeriesSnapshot.from_json` reads both forms. Every 010 snapshot loads with no marks, no guest and
  no away host.
- `to_json` writes the plain string form for unmarked points, so a snapshot with no marks, guest or
  away host is byte-identical to 010's.

---

## 3. Records and values (`app/podcasts/services/`)

### 3.1 `EpisodeSettings`

New in `episode_settings.py`. It is a frozen dataclass, imported by prompts, the policy and the
service.

| Field | Type |
|---|---|
| `style` | `EpisodeStyle` |
| `line_length` | `HostLineLength` |
| `invite_frequency` | `InviteFrequency` |
| `learner_role` | `str` |
| `today_subject` | `str \| None` |
| `covered_personality` | `str \| None` |

Behaviour:
- `defaults(learner_role)`;
- `from_ids(...)`, which raises `ValueError` on an unknown id;
- `summary()`, which builds the setup's one-line summary from the catalogue labels.

### 3.2 `EpisodeRecord` and `NewEpisode` (changed)

Each gains `settings: EpisodeSettings | None`:
- None on a record means the episode is pre-feature;
- `NewEpisode.settings` is always set for new starts.

`SQLitePodcastStorage.create_episode` writes the settings row in its existing transaction, and
`get_episode` left-joins it.

### 3.3 `SeriesSettings` (new, in `series_settings.py`)

| Field | Type |
|---|---|
| `format` | `str` |
| `length` | `str` |
| `style` | `str` |
| `line_length` | `str` |
| `invite_frequency` | `str` |
| `learner_role` | `str` |

Behaviour:
- `standard(show: KeptShow)` returns One host, Medium, Balanced, Medium lines, Sometimes and the
  show's role. It is the one definition of "the show's standard settings".
- `with_changes(values, names)` returns a copy with the named fields taken from `values`. It raises
  `ValueError` for a name outside `SERIES_SETTING_NAMES`.
- `is_standard_for(show)` drives the "Use the show's standard settings" action.

`SeriesRecord` gains `settings: SeriesSettings`. Storage fills it from the row, or from `standard`
when there is none.

### 3.4 `SeriesStorage` (two new abstract methods, one changed)

| Method | Contract |
|---|---|
| `hosts_present(series_id) -> Mapping[int, frozenset[str]]` | For each series episode (conversation id), the names in its `podcast_hosts`, guests included |
| `reset_settings(series_id) -> bool` | Delete the settings row. False for an unknown series. True even when no row existed |
| `create(show_row_id, language, hosts, settings)` | *Changed*: also inserts the settings row (episode 1) |

`RememberedPoint` gains `conversation_id: int`, so `_snapshot` can join points to `hosts_present`.

The settings upsert for a later episode belongs to the episode's start. `NewSeriesLink` gains
`settings_update: SeriesSettings | None`. `SQLitePodcastStorage.create_episode` applies it with the
link row, in the same transaction, as 010 adds the link.

### 3.5 Snapshot values (`series_snapshot.py`, changed)

| Value | Fields |
|---|---|
| `RememberedLine` (new) | `text: str`, `missed_by: tuple[str, ...] = ()` |
| `SeriesSnapshot` | `topics_covered` and `about_learner` become `tuple[RememberedLine, ...]`; it gains `guest_slot: str \| None = None` and `away_host_name: str \| None = None` |
| `SeriesBrief` | Gains `guest_name: str \| None` (from the cast and `guest_slot`), `away_host_name`, and `missed_names(line) -> tuple[str, ...]` (slots present in the cast, resolved to names) |

### 3.6 Streaming values

| Value | Module | Fields |
|---|---|---|
| `LinePart` | `services/spoken_parts.py` | `stream_id: str`, `index: int`, `text: str`, `audio_url: str \| None` |
| `SpokenParts` | same | `begin(stream_id, voice_key, language) -> None`, `add(stream_id, text) -> LinePart`, `audio(stream_id, index, timeout) -> Path`, `assemble(stream_id, message_id) -> Path \| None`, `discard(stream_id)` |
| `SentenceSplitter` | `services/sentences.py` | `feed(token) -> list[str]`, `flush() -> str` |
| `StreamingSanitiser` | `services/sanitiser.py` | `clean_sentence(text) -> SentenceVerdict(text, is_cut)`; `was_trimmed`; `address() -> LineAddressResult` once the line is flushed |

### 3.7 Line values (changed, research R19)

| Value | Module | Change |
|---|---|---|
| `Ask` | `services/turn_policy.py` | New `StrEnum`: `REQUIRED`, `ALLOWED`, `NONE` |
| `LineCue` | same | `invites_learner: bool` becomes `ask: Ask`, and it gains `asker: str \| None` (the slot or `"learner"` whose question an `answer` replies to, rebuilt from the previous line). `is_settle_invite` is true when `ask` is not `NONE` and it is a settle moment |
| `LineFacts` | same | Gains `ask: Ask` and `addressee: str \| None`. `_line_facts` fills `ask` from the column, or from `invites_learner` when NULL |
| `LineAddressResult` | `services/line_address.py` (new) | `addressee: str \| None`, `text: str` (tags removed), `is_from_tag: bool` |
| `LineAddress` | same | `for_episode(cast, learner_label, speaker_slot, language, is_listening)`; `read(text) -> LineAddressResult` |
| `NewHostLine` / `LineRecord.host` | `services/storage.py` | Gain `ask` and `addressee`. `invites_learner` is computed by the caller |
| `SubjectSuggester` | `services/subject_suggestions.py` (new) | `suggest(request: SubjectRequest) -> tuple[str, ...]` |
| `SubjectRequest` | same | `show: ShowBrief`, `languages`, `interests`, `covered: tuple[str, ...]`, `avoid: tuple[str, ...]` |

---

## 4. Turn policy (changed: `services/turn_policy.py`)

`EpisodeState` gains `talk: HostTalk`. `LoadedEpisode.state` sets it with `host_talk_for(record.settings)`.

| Rule | Legacy | Configured |
|---|---|---|
| `Ask` of the cue | One host: `required`. Panel: hazards (0.25, 0.45, 0.60) give `required`, deadline 4. Wrap-up: `required`. Sign-off: `none` | Hazards of the episode's `InviteFrequency` give `allowed`, `required` at deadline 4 and on every Often line, in every speaking format. Wrap-up: `required`. Sign-off, an answer after the wrap-up, Listen, and `open`/`greet` in a two-host format: `none`. Panel's balance rule kept |
| Stored `invites_learner` | `ask == required` | `ask == required` or `addressee == learner`, except `open`/`greet` in a two-host format (R19) |
| Next speaker | run cap > addressed host > balance > hand-over > preferred > random | run cap > addressed host > **addressee of the last host line** > balance > hand-over > preferred > random |
| Discussion intent | `discuss` | After a wrap-up: research R21's table. Otherwise `answer` if the learner's last line contains `?`, or the last host line is for the other host and ends with `?`; else `follow_up` if the last learner line had ≥ 2 `?` and the one host line since was `answer`; else a Style-weighted draw of `react` / `explain` / `story` |
| `open`, `greet`, `wrap_up`, `sign_off` | Unchanged | Same positions; configured wording (R20, R21); `sign_off` also follows the learner's last thought (R21) |

**Invariants**, each with a seeded property test (addressees fed by the test):
- never five host lines in a row without an invitation in a speaking format (SC-005);
- an `answer` line always follows a learner line with `?`, and a host line for the other host that
  ends with `?`;
- a host line whose addressee is the learner is always followed by the learner's turn;
- after a host line addressed to the other host, that host speaks next unless the run cap forbids it;
- a sign-off never invites;
- in a speaking format, after the wrap-up and a learner reply without `?` (or a pass), the next host
  line is `sign_off` (SC-015).

---

## 5. Validation (Start, data-model rules for `POST /episodes`)

### 5.1 Episode settings (every start)

| Check | Failure (422 unless noted) |
|---|---|
| `style`, `line_length` and `invite_frequency` are catalogue ids | "That {setting} isn't in the list. Pick one of the listed ones." |
| `learner_role` is in `LEARNER_ROLES` | "Your role must be guest, co-host or caller." |
| `today_subject` ≤ 120 characters after trimming | "Today's subject can be at most 120 characters." |
| `today_subject` passes `SubjectCheck` | "That subject can't be used for an episode. Change it or clear it, then start." |
| `SubjectCheck` provider failure | **503** with the provider's message |
| Listen | `invite_frequency` and `learner_role` are ignored, and stored as default and show role |

### 5.2 Series episodes after the first

These apply in addition to 010's checks: the hosts match the series, and the name does not clash.

| Check | Failure |
|---|---|
| Every name in `from_now_on` is in `SERIES_SETTING_NAMES` | 422 "That setting can't be kept for later episodes." |
| `from_now_on` is empty on a one-off | 422 "Only a series keeps settings for later episodes." |
| At most one guest | 422 "Only one guest can join an episode." |
| The guest's slot is used by the format | 422 "That guest has no seat in this format. Pick Panel, or invite them in the host's place." |
| The guest's name is not any series host's nor the learner's | 422 "{name} is already a host of this show. Invite another guest." / the 010 name-clash message |
| The guest's voice speaks the language, and its personality is known | 007's host messages |
| The guest's personality and voice differ from the other present host's (voice only with ≥ 2 installed) | 007's pair messages |

Episode 1 of a series: `from_now_on` is ignored, because every setting becomes the series' usual one
(FR-014). A guest is refused: 422 "A guest can join from the second episode."

### 5.3 What a start writes

| Start | Episode settings row | Series settings | Preferences |
|---|---|---|---|
| One-off | ✓ | — | `last_style`, `last_line_length`, `last_invite_frequency`, plus 007's `last_format` and name |
| Series, episode 1 | ✓ | insert from this episode | 007's `last_format` and name only |
| Series, later | ✓ | upsert of the `from_now_on` fields, if any | same |

### 5.4 Subject suggestions (`POST /api/podcasts/subject-suggestions`, research R20)

| Check | Failure |
|---|---|
| `series_id`, when given, is a series of the current practice language | 404 `SERIES_GONE` (010: "That series isn't there any more. Open the show again.") |
| `avoid` has at most `SUBJECT_AVOID_MAX` entries, each ≤ 120 characters | 422 "Too many subjects to skip. Close the suggestions and try again." |
| The provider fails | 503 with the provider's message |

Nothing is written. The reply is trimmed and filtered as research R20 describes.

---

## 6. State transitions

### 6.1 A setting on a continuing series' setup (frontend, per setting)

```text
usual ──change──▶ asking ──Just this episode──▶ this-episode ──Start──▶ (episode only)
                    │                                │
                    ├──This and later episodes──▶ from-now-on ──Start──▶ (series value)
                    └──Escape / Cancel──▶ usual (change reverted)
this-episode / from-now-on ──change again──▶ same scope
this-episode / from-now-on ──set back to usual value──▶ usual
any ──leave the screen──▶ discarded
```

### 6.2 A host chair in a continuing series' setup

```text
regular ──Invite a guest… → personality → cast──▶ guest (this episode)
guest ──Another guest──▶ guest (recast)
guest ──Remove guest──▶ regular
regular ──Recast… (confirmed)──▶ regular (new host, from now on; 010, immediate)
One host series, Format → Panel, Just this episode ──▶ second chair: expert guest (auto-cast)
One host series, Format → Panel, from now on ──▶ second chair: the series' second host (new to the show)
```

### 6.3 A streamed host line (backend)

```text
cue chosen → line_started → [sentence → read & strip address tag → sanitise → (cut? stop)
  → (tag only? no part) → synthesise → line_part]×n
  → addressee → invites = talk.invitation(ask, addressee) → store line → assemble WAV → line → done
error before any part → retry once (empty or retryable) → else error frame
error after a part   → end session, discard parts → error frame with stream_id
```
