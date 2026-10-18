# Data Model: Recurring Podcast Shows

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Research**: [research.md](research.md)

Every change is additive. There are five new tables via `create_all()`, all in `app/podcasts/models.py`.
Existing tables gain **no columns**, and no existing row is updated. The tables 007 created
(`podcast_episodes`, `podcast_hosts`, `podcast_host_lines`, `podcast_preferences`) keep their
shape.

```text
conversations ─┬─< podcast_episodes ──< podcast_series_episodes >── podcast_series ─┬─< podcast_series_hosts
               │                         (one-off episodes: no row)                ├─< podcast_series_memories
               └────────────────────────────────────────────────< podcast_series_memories (source episode)
podcast_shows ──< podcast_series   (unique per show × target_language)
```

---

## 1. Catalogue changes (`backend/app/podcasts/catalog.py`)

| Name | Change |
|---|---|
| `SHOW_SOURCES` | + `"suggested"` (Find a new show, research R10). `podcast_episodes.show_source` is `String(12)`, so it fits. |
| `EPISODE_KINDS` | new: `("one_off", "series")`. Default `"one_off"`, so the 007 request shape is unchanged. |
| `MAX_REMEMBERED_TOPICS` | new: `10` (research R7) |
| `MAX_REMEMBERED_ABOUT_LEARNER` | new: `8` |
| `MAX_POINTS_PER_EPISODE` | new: `3` learner points per memory reply |
| `REMEMBERED_POINT_MAX_LENGTH` | new: `160` characters |
| `SERIES_SECTION_MAX_LENGTH` | new: `1800` characters, the budget the series prompt section is tested against |
| `MIN_LINES_TO_REMEMBER` | new: `2` |
| `MEMORY_CHUNK_CHARACTERS` | new: `6000` (the summariser's budget, 007 R14) |
| `MEMORY_WAIT_SECONDS` | new: `30`, the longest `POST /series/{id}/memory?wait=true` holds (research R6) |
| `SUGGESTION_SEEDS` / `MIN_SUGGESTIONS` / `INTEREST_SEEDS` | new: `5` / `3` / `3` (research R10) |

`SHOW_TEMPLATES` is **unchanged**: same shows, same order (FR-015).

---

## 2. Tables

### 2.1 `podcast_shows`: a show the learner has state for (research R1)

| Column | Type | Rules |
|---|---|---|
| `id` | INTEGER PK | |
| `template_id` | VARCHAR(100) NULL, UNIQUE | Set for a ready-made show, and then every content column is NULL |
| `source` | VARCHAR(12) NOT NULL | One of `SHOW_SOURCES` |
| `title` | VARCHAR(200) NULL | Learner-made only; ≤ `TITLE_MAX_LENGTH` |
| `premise` | TEXT NULL | Learner-made only |
| `topic` | VARCHAR(200) NULL | Learner-made only |
| `learner_role` | VARCHAR(12) NULL | Learner-made only; one of `LEARNER_ROLES` |
| `lead_personality`, `second_personality` | VARCHAR(30) NULL | Learner-made only; catalogued and different |
| `lead_angle`, `second_angle` | TEXT NULL | Learner-made only |
| `favourited_at` | DATETIME NULL | NULL means not a favourite. Not per language |
| `last_played_at` | DATETIME NULL | Set when any episode of the show starts |
| `created_at` | DATETIME NOT NULL | |

**Invariants** (checked in `ShowLibrary`, tested in the storage contract):
- the row is a ready-made show (`template_id` in `SHOW_TEMPLATES`, `source = ready_made`) **or** a
  learner-made one (`template_id` NULL, every content column set), never both;
- a ready-made row exists only while it is a favourite or has a series;
- a learner-made row exists only while it is a favourite, has been played, or has a series
  (FR-019).

### 2.2 `podcast_series`: one show in one practice language (research R2)

| Column | Type | Rules |
|---|---|---|
| `id` | INTEGER PK | |
| `show_id` | FK → `podcast_shows.id` ON DELETE CASCADE | |
| `target_language` | VARCHAR(10) NOT NULL | A catalogued practice language |
| `created_at` | DATETIME NOT NULL | |

UNIQUE (`show_id`, `target_language`). Created by the first series episode, deleted by reset.

### 2.3 `podcast_series_hosts`: the series' hosts, both slots always

| Column | Type | Rules |
|---|---|---|
| `id` | INTEGER PK | |
| `series_id` | FK → `podcast_series.id` ON DELETE CASCADE | |
| `slot` | VARCHAR(8) NOT NULL | `lead` or `second` |
| `name` | VARCHAR(40) NOT NULL | 1–40 characters; differs from the other slot's (casefold) |
| `personality` | VARCHAR(30) NOT NULL | Catalogued; differs from the other slot's |
| `voice_key` | VARCHAR(200) NOT NULL | Speaks the series' language |
| `show_role` | VARCHAR(20) NOT NULL | `SHOW_ROLE_BY_SLOT[slot]` |
| `angle` | TEXT NULL | |
| `joined_after_episodes` | INTEGER NOT NULL DEFAULT 0 | The episode count when this host joined: 0 for an original host, the count at recast otherwise |

UNIQUE (`series_id`, `slot`). A recast **updates** the slot's row in place: name, personality,
voice, angle cleared, and `joined_after_episodes` set to the current count.

Derived: a host **is new in episode N** when `joined_after_episodes = N − 1` and N > 1. They
**have history** when `joined_after_episodes < episode_count`.

### 2.4 `podcast_series_episodes`: which episodes belong to a series (research R3, R5, R6)

| Column | Type | Rules |
|---|---|---|
| `conversation_id` | INTEGER PK, FK → `podcast_episodes.conversation_id` ON DELETE CASCADE | |
| `series_id` | FK → `podcast_series.id` ON DELETE CASCADE, indexed | |
| `episode_number` | INTEGER NOT NULL | The series' episode count + 1 when the episode started |
| `snapshot` | TEXT NOT NULL | JSON `SeriesSnapshot` (§3), fixed for the episode's life |
| `remembered_up_to_message_id` | INTEGER NULL | The last message the memory keeper has read; NULL means none |

No row means a one-off episode, or one recorded before this feature (FR-007, FR-022).

### 2.5 `podcast_series_memories`: what the hosts remember (research R6, R7)

| Column | Type | Rules |
|---|---|---|
| `id` | INTEGER PK | |
| `series_id` | FK → `podcast_series.id` ON DELETE CASCADE, indexed | |
| `conversation_id` | FK → `conversations.id` ON DELETE CASCADE | The episode the point came from |
| `kind` | VARCHAR(8) NOT NULL | `topic` or `learner` |
| `conversation_language` | TEXT NOT NULL | 1–160 characters; what the snapshot carries |
| `english` | TEXT NOT NULL | 1–160 characters; what the learner sees |
| `created_at` | DATETIME NOT NULL | Recency order for the caps |

Rules:
- at most one `topic` row per (`series_id`, `conversation_id`): a re-read episode replaces its
  topic;
- after every write, at most `MAX_REMEMBERED_TOPICS` topic rows and
  `MAX_REMEMBERED_ABOUT_LEARNER` learner rows remain per series, keeping the newest. The pruning
  happens in the same transaction as the write.

---

## 3. Domain value objects (`backend/app/podcasts/services/`)

| Object | Fields | Behaviour |
|---|---|---|
| `ShowRef` | `template_id: str \| None`, `saved_show_id: int \| None` | Exactly one is set; `of(draft)` builds it from a `ShowDraftModel` |
| `KeptShow` | `show_row_id`, `ref`, `source`, `title`, `premise`, `topic`, `learner_role`, `personalities`, `angles`, `is_favourite`, `last_played_at` | For a ready-made show, the content is read from `SHOW_TEMPLATES` |
| `SeriesHost` | `slot`, `name`, `personality_id`, `voice_key`, `show_role`, `angle`, `joined_after_episodes` | `to_host() -> Host`; `is_new_in(n)`; `has_history(count)` |
| `SeriesRecord` | `series_id`, `show`, `language`, `hosts: tuple[SeriesHost, SeriesHost]`, `episode_count`, `unfinished: EpisodeRef \| None` | `next_episode_number = episode_count + 1`; `matches(draft_hosts) -> bool` (slot, name, personality, voice) |
| `RememberedPoint` | `point_id`, `kind`, `conversation_language`, `english`, `episode_number` | |
| `SeriesSnapshot` | `episode_number`, `topics_covered: tuple[str, ...]`, `about_learner: tuple[str, ...]`, `new_host_slots: tuple[str, ...]` | `to_json()` / `from_json()`; round-trips exactly. Built from the bounded memory at start |
| `SeriesBrief` | the snapshot, plus host names resolved from the episode's cast | What `build_standing_prompt` and `render_cue` take. `None` for a one-off |
| `MemoryReply` | `topic: PointText \| None`, `about_learner: tuple[PointText, ...]` | Parsed from the structured reply; ≤ 3 learner points; each text trimmed and cut to 160 characters |

`NewEpisode` (007) gains `series: NewSeriesLink | None`, where `NewSeriesLink` is
`(series_id, episode_number, snapshot)`. `create_episode` writes the link row in the **same
transaction** as the conversation, the episode and its hosts, so a series episode cannot exist
without its link or the reverse.

`EpisodeRecord` (007) gains `series: EpisodeSeriesFacts | None` (`series_id`, `episode_number`,
`snapshot`), read with a left join, so `LoadedEpisode` can build its `SeriesBrief`.

---

## 4. Storage interfaces (ABCs, ISP)

`PodcastStorage` (007) keeps its methods. The new methods go in two small ABCs beside it, both
implemented by SQLite classes in `services/`:

**`ShowLibraryStorage`**
- `keep(draft_content) -> KeptShow`: get-or-create, by ref or by content for an unsaved draft;
- `get(ref) -> KeptShow | None`;
- `set_favourite(ref_or_content, is_favourite) -> KeptShow | None`: returns None when unfavouriting
  deleted the row (§2.1);
- `touch_played(show_row_id)`;
- `list_mine(language) -> list[ShelfEntry]`: research R9's union and order.

**`SeriesStorage`**
- `find(show_row_id, language) -> SeriesRecord | None`;
- `get(series_id) -> SeriesRecord | None`;
- `create(show_row_id, language, hosts) -> SeriesRecord`;
- `recast(series_id, host: SeriesHost) -> SeriesRecord`;
- `reset(series_id) -> bool`;
- `remembered(series_id) -> tuple[RememberedPoint, ...]`;
- `pending_episodes(series_id) -> tuple[PendingEpisode, ...]`: link rows with lines after the
  marker;
- `remember(series_id, conversation_id, reply: MemoryReply, up_to_message_id)`: writes, prunes
  (§2.5) and moves the marker, all in one transaction.

The factory composes both with `PodcastStorage` over one session per request. The memory keeper
gets its own session from `SessionLocal`, built in the factory only.

---

## 5. State and transitions

### 5.1 A show, from the learner's point of view

```text
ready-made, no state ──favourite──► kept (favourite) ──unfavourite, no series──► no state
        │                                   │
        └──series episode 1──► kept (series) ◄──┘
                                   │
                                 reset ──► kept only if favourite, else no state

learner-made draft (unsaved) ──favourite or any episode──► kept ──unfavourite──► kept if played or series, else deleted
```

### 5.2 A series

```text
(none) ──Start, kind=series──► 1 episode ──Start next──► n episodes
   ▲                            │    ▲                     │
   └────────── reset ───────────┴────┴── recast(slot): hosts change, count unchanged
```

**Start, kind=series** on show S in language L:
1. **Validate**: `validate_draft` as in 007, with the series name-clash wording (research R8).
2. **Keep the show**: `keep(draft)`, then `touch_played`.
3. **Find the series** for (S, L). If there is none, create it from the draft's two hosts
   (`joined_after_episodes = 0`). Otherwise the draft's hosts must match the series' hosts, or the
   start is refused with 409 `SERIES_HOSTS_CHANGED`.
4. **Take the snapshot** from the bounded memory: `episode_number = count + 1`, and
   `new_host_slots` = the slots with `joined_after_episodes = count` when count ≥ 1.
5. **Create the episode** with `series = NewSeriesLink(...)`. The participating hosts are copied
   from the series for the format's slots.

**Start, kind=one_off**: steps 1 and 2 for a learner-made show (FR-014), and for a ready-made show
only `touch_played` when its row exists. Then 007's start, unchanged.

### 5.3 Memory of one series episode

```text
started (marker NULL) ──lines──► pending ──catch-up──► remembered up to message m ──more lines──► pending …
```

Catch-up runs after a series sign-off and on `POST /series/{id}/memory`.

A series' `memory_status` is derived, never stored:
- `running` while `MemoryCatchUps` holds the series;
- otherwise `pending` when any of its episodes has at least `MIN_LINES_TO_REMEMBER` lines after
  its marker;
- otherwise `up_to_date`.

Before a series start, the setup screen waits on the catch-up (`?wait=true`) whenever the status
is not `up_to_date`, showing a "catching up" message. `POST /episodes` itself never waits
(research R6).

---

## 6. Validation rules at the boundary (additions to 007 §6)

| Input | Rule | Response |
|---|---|---|
| `StartEpisodeRequest.kind` | `one_off` or `series` | 422 (pydantic) |
| `ShowDraftModel.saved_show_id` | When set, `source` is learner-made and the show exists | 404 "That show isn't kept any more. Pick another one." |
| `ShowDraftModel.show_id` | When `source = ready_made`, in `SHOW_TEMPLATES` | 422 (as 007) |
| A series draft with episodes | Hosts equal the series' hosts | 409 "This show's hosts changed. Open the show again." |
| A series host's name equals `learner_name` | casefold compare | 422 "{name} has the same name as you. Change the name the hosts call you." |
| Recast `slot` | `lead` or `second` | 422 |
| Recast `personality_id` | Optional; catalogued; not the other host's | 422 "{other} already has that personality. Pick another one." |
| Recast / series in another language | `series.language == settings.target_language` | 422 `LANGUAGE_CHANGED` |
| `discover.avoid_titles` | ≤ 50 entries, each ≤ 200 characters | 422 |
| Unknown `series_id` | | 404 "That series isn't there any more. Open the show again." |
