# Interface Contracts: Recurring Podcast Shows

**Feature**: [spec.md](../spec.md) | **Data model**: [data-model.md](../data-model.md) |
**Research**: [research.md](../research.md) | **Builds on**: [007 contracts](../../007-podcast-mode/contracts/api.md)

All paths are under `/api`. Unless a section says otherwise, the shapes of 007's endpoints are
unchanged, and every new field is **added** (no field is renamed or removed). The shared errors of
007 apply: `503` for any `LLMError` with the provider's message, `503` for `VoiceUnavailable`,
`404` with a plain message, and `409` with a plain next step.

Sections:
- **§1–§2**: extended catalogue and episode shapes;
- **§3–§8**: new endpoints;
- **§9**: prompts (internal contract);
- **§10**: module interfaces;
- **§11**: UI and E2E.

---

## 1. `GET /api/podcasts/catalog` (extended)

Two changes:
- `shows` is now a list of **`ShowListing`**: a 007 `ShowDraft` plus three read-only fields;
- a new list, `my_shows`, also of `ShowListing`.

```json
{
  "language": "es",
  "…": "formats, lengths, personalities, voices: unchanged",
  "shows": [ShowListing, "… the 8 ready-made shows, in catalogue order"],
  "my_shows": [ShowListing, "… possibly empty"]
}
```

**`ShowListing`**: a `ShowDraft`, plus:

```json
{
  "source": "ready_made",
  "show_id": "big-little-questions",
  "saved_show_id": null,
  "title": "Big Little Questions",
  "premise": "Everyday curiosities, from why toast lands butter-side down onwards.",
  "topic": "everyday curiosities",
  "learner_role": "guest",
  "language": "es",
  "hosts": [
    {"slot": "lead", "name": "Hugo", "personality_id": "curious_interviewer", "voice_key": "es_ES-davefx-medium", "show_role": "host", "angle": null},
    {"slot": "second", "name": "Inés", "personality_id": "expert", "voice_key": "es_AR-daniela-high", "show_role": "co_host", "angle": null}
  ],
  "is_favourite": true,
  "series": SeriesSummary
}
```

**`SeriesSummary`** (`null` when the show has no series in this language):

```json
{
  "series_id": 4,
  "episode_count": 1,
  "next_episode_number": 2,
  "unfinished_episode": {"conversation_id": 81, "episode_number": 1}
}
```

`unfinished_episode` is `null` when the latest series episode has finished.

| Guarantee | Test |
|---|---|
| `shows` holds the same ready-made shows in the same order on every call (FR-015) | contract |
| A show with a series in this language lists the series' hosts; one without lists `cast_template`'s hosts, the same on every call for a given language and learner name (FR-010) | contract + unit |
| `my_shows` is exactly: the favourites, the shows with a series in this language, and the played learner-made shows, newest activity first (research R9) | integration |
| A ready-made show in `my_shows` is also in `shows`, with equal fields | contract |
| `my_shows` is `[]` for a learner with no favourites, series or kept shows (US4-4) | contract |
| Sending a `ShowListing` back as `POST /episodes`'s `show` is accepted (the extra fields are ignored) | contract |

`ShowDraft` (in requests) gains **`saved_show_id: int | null`** (default null), and `source` may
now also be `"suggested"`.

---

## 2. Episodes (extended)

### `POST /api/podcasts/episodes`

The request gains **`kind`**: `"one_off"` (the default, which is 007's behaviour) or `"series"`.

```json
{"show": ShowDraft, "format": "panel", "length": "medium", "learner_name": "Sam", "kind": "series"}
```

| Case | Result |
|---|---|
| `kind = series`, no series yet for (show, language) | 201. The series is created from `show.hosts`; this is episode 1 |
| `kind = series`, series exists, `show.hosts` match the series' hosts | 201. Episode `next_episode_number`, with the series' hosts and a memory snapshot |
| `kind = series`, hosts differ | **409** "This show's hosts changed. Open the show again." |
| A series host's name equals `learner_name` | **422** "{name} has the same name as you. Change the name the hosts call you." |
| `saved_show_id` unknown | **404** "That show isn't kept any more. Pick another one." |
| Learner-made show, either kind | The show is kept (`saved_show_id` assigned) and `last_played_at` is set (FR-014) |
| `kind = one_off` | No series row is read or written (FR-007) |

### `EpisodeResponse` (`POST /episodes`, `GET /episodes/{id}`)

The response gains two fields:
- **`series`**: `{"series_id": 4, "episode_number": 2}` for a series episode, or `null`;
- **`show.saved_show_id`**: the kept show's id, or `null`.

The episode header reads "Big Little Questions · Episode 2"; a one-off reads "Big Little
Questions · One-off".

### `GET /api/podcasts/episodes` (Past Chats rows)

Each row gains **`episode_number: int | null`**. Episodes from before this feature have `null`
(FR-022).

---

## 3. `PUT /api/podcasts/favourites`

Marks or unmarks a show as a favourite (FR-012). The request takes the whole draft, so an unsaved
suggestion can be favourited and kept in one step (FR-019).

```json
{"show": ShowDraft, "is_favourite": true}
```

**200**: the updated `ShowListing`. A favourited learner-made draft now has its `saved_show_id`.

**204** instead when unfavouriting deleted the show's row: a learner-made show never played and
with no series, or a ready-made show with no series (data-model §2.1).

| Guarantee | Test |
|---|---|
| A favourite is the same in every practice language | integration |
| It persists across a restart (a new engine over the same file) | integration |
| Unfavouriting a show with a series keeps it in `my_shows` (US4 independent test) | integration |
| Favouriting the same unsaved draft twice keeps one show | integration |

---

## 4. `POST /api/podcasts/shows/discover` (Find a new show)

```json
{"avoid_titles": ["Night Trains of Europe", "…titles already shown this visit"]}
```

**200**

```json
{"suggestions": [ShowDraft, ShowDraft, ShowDraft, "… 3 to 5, each with source = suggested"]}
```

The response follows research R10:
- no suggestion's normalised title matches a ready-made show, a show in `my_shows`, or an
  `avoid_titles` entry (FR-017);
- nothing is stored (FR-019).

**503** `{"detail": "Find a new show didn't come up with enough shows this time. Please try
again."}` when fewer than 3 survive after one top-up call. A provider failure is the provider's
own 503 message (FR-020).

| Guarantee | Test |
|---|---|
| ≥ 3 suggestions, or the plain 503 | contract with a scripted structured provider |
| Unsuitable, unreadable and duplicate shows are dropped, never returned (FR-018) | unit (`ShowDiscovery`) |
| With interests, 3 of the 5 seeds are interests; without, all 5 are built-in topics (US5-4) | unit, seeded |
| The prompt names the languages, never their codes | unit |
| No row is written by this endpoint | integration (table counts) |

---

## 5. `GET /api/podcasts/series/{series_id}`

The setup screen's view of a series: who the hosts are and what they remember (FR-011).

**200**

```json
{
  "series_id": 4,
  "language": "es",
  "show": ShowListing,
  "episode_count": 3,
  "next_episode_number": 4,
  "unfinished_episode": null,
  "hosts": [
    {"slot": "lead", "name": "Hugo", "personality_id": "curious_interviewer", "personality_label": "Curious interviewer",
     "voice_key": "es_ES-davefx-medium", "show_role": "host", "has_history": true, "is_new_next_episode": false},
    {"slot": "second", "name": "Inés", "personality_id": "expert", "personality_label": "Expert",
     "voice_key": "es_AR-daniela-high", "show_role": "co_host", "has_history": true, "is_new_next_episode": false}
  ],
  "remembered": {
    "topics": [{"point_id": 17, "text": "Why we yawn", "episode_number": 2}],
    "about_learner": [{"point_id": 12, "text": "You hate mornings.", "episode_number": 1}]
  }
}
```

`text` is the English version. **404** "That series isn't there any more. Open the show again."

## 6. `POST /api/podcasts/series/{series_id}/hosts/{slot}/recast`

```json
{"language": "es", "learner_name": "Sam", "personality_id": "joker"}
```

`personality_id` is optional: without it, a random personality the other host does not have is
chosen.

**200**: the updated series (§5). The recast slot has `has_history: false` and
`is_new_next_episode: true`.

The rules follow research R8:
- the name is new, unlike the other host's and the learner's, and from the language's name bank
  for the voice's gender;
- the voice follows 007's interpretation 6;
- the other slot's row, the episode count and the memories are unchanged (FR-009).

**422**: language changed (`LANGUAGE_CHANGED`); personality uncatalogued or the other host's.
**404**: unknown series.

## 7. `DELETE /api/podcasts/series/{series_id}` (Start over)

**204**. The series, its hosts, its links and its memories are deleted. The episodes stay in Past
Chats with `episode_number: null` from then on (FR-011). **404** for an unknown series.

## 8. `POST /api/podcasts/series/{series_id}/memory`

Starts a background catch-up of the series' pending episodes (research R6). It never waits for
the model.

**202** `{"status": "started" | "running" | "up_to_date"}`. **404** for an unknown series.

| Guarantee | Test |
|---|---|
| A catch-up reads only the lines after each episode's marker, and moves the marker | integration with a scripted structured provider |
| Learner points come only from chunks with learner lines; a Listen episode adds a topic only | unit + integration |
| The caps hold after any number of catch-ups (FR-006) | property test, seeded, 200 random catch-up sequences |
| A provider failure leaves the memory and the marker unchanged, and is logged | integration |
| Two concurrent requests start one catch-up | unit (`MemoryCatchUps`) |
| A series sign-off schedules a catch-up through `EpisodeEndings`; a one-off sign-off does not | integration |

---

## 9. Prompts (internal contract, unit-tested)

**One-off episodes**: `build_standing_prompt(show, cast, label, languages, level, series=None)`
and `render_cue(cue, cast, label, series=None)` return exactly 007's text. A golden test pins
both for every format.

**Series episodes**: the standing prompt gains one section, built from the snapshot, before the
line rules. It contains:
- "This is episode N of a continuing show." (or "the first episode of a continuing show" when
  N = 1);
- "Earlier episodes covered: …"
- "What {label} has told you before: …"
- the rules (FR-005): refer back to these points where it fits; choose a subject within the show's
  topic that is not in the covered list; never claim to remember anything not listed; introduce
  {new host} as new to the show, who does not know the earlier episodes;
- at most `SERIES_SECTION_MAX_LENGTH` characters, whatever the snapshot holds.

The cues change in two places:
- **`open`** in a series episode with N > 1: welcome {label} back, say the show is continuing, and
  bring up one thing from earlier episodes;
- **`greet`** by a new host: introduce yourself as new to the show.

A new lead host is introduced through the standing prompt, and their `open` adds "introduce
yourself as the show's new host".

**Memory**: `MEMORY_JSON_SCHEMA` is `{topic: {conversation_language, english} | null, about_learner:
[{conversation_language, english}] (maxItems 3)}`. The prompt contains:
- the labelled transcript chunk (host names; the learner as "Learner");
- the points already remembered;
- rules: about the learner only from lines labelled Learner; nothing a host said about
  themselves; no guesses; an empty list when there is nothing; the subject of the episode as one
  short phrase.

**Discovery**: `DISCOVERY_JSON_SCHEMA` is `{shows: [SHOW_JSON_SCHEMA item] (minItems 1, maxItems 5)}`.
The prompt lists the seeds and the titles to avoid, and reuses the generator's suitability and
field rules.

---

## 10. Module interfaces

### `app.podcasts` (package root: unchanged)

`router`, `PODCAST_SCENARIO_ID`, `PodcastMessageVoices` and `PodcastSpeakerNames`. Every new piece
is internal.

New internal modules:
- `series_routes.py`: §3, §5–§8;
- `discovery_routes.py`: §4;
- `services/library.py`: `ShowLibrary`, `ShowRef`;
- `services/series.py`: `SeriesService`, covering start resolution, recast and reset;
- `services/series_memory.py`: `SeriesMemoryKeeper`, `MemoryCatchUps`, the memory prompt and
  parser;
- `services/discovery.py`: `ShowDiscovery`, `SuggestionSeeds`;
- `services/series_storage.py`: the `ShowLibraryStorage` and `SeriesStorage` ABCs and their
  records;
- `services/sqlite_series_storage.py`;
- `services/episode_endings.py`: the `EpisodeEndings` ABC, one method:
  `episode_finished(conversation_id)`.

**Composition-root exception (extended)**: `services/factory.py` may also import
`services/series_storage`, `services/sqlite_series_storage`, `services/series_memory` and
`services/episode_endings`. `tests/unit/test_module_boundaries.py` is extended to enforce it.

### Changes inside `app.podcasts` (007 code)

| Module | Change |
|---|---|
| `catalog.py` | the §1 constants of the data model; `SHOW_SOURCES` + `suggested` |
| `models.py` | five new tables |
| `schemas.py` | `ShowListing`, `SeriesSummaryModel`, `SeriesDetailResponse`, `RecastRequest`, `FavouriteRequest`, `DiscoverRequest`; `kind` on `StartEpisodeRequest`; `saved_show_id` on `ShowDraftModel`; `series` on `EpisodeResponse`; `episode_number` on `EpisodeSummaryRow` |
| `prompts.py` | an optional `series` argument on `build_standing_prompt` and `render_cue`; the memory and discovery prompts and schemas |
| `routes.py` | `get_catalog` adds the listings; `start_episode` delegates to `SeriesService`; the new routers are included |
| `services/storage.py`, `sqlite_storage.py` | `NewEpisode.series`, `EpisodeRecord.series`; the link row in `create_episode`'s transaction |
| `services/episodes.py` | `LoadedEpisode.series_brief`, passed to the prompt and the cues |
| `services/cues.py` | passes the brief to `render_cue` |
| `services/episode_turns.py` | `EpisodeDependencies.endings`; `_after` reports a finished series episode |
| `services/generator.py` | the show parser is shared with discovery |
| `responses.py` | listings, series fields |

### Outside `app.podcasts`

| Module | Change |
|---|---|
| `services/factory.py` | `get_show_library`, `get_series_storage`, `get_series_memory_keeper`, `get_memory_catch_ups`, `get_episode_endings` |
| `database.py` | nothing: the new models are in `app/podcasts/models.py`, which is already imported |

No change to `prompts/templates.py`, `conversation_levels`, `conversation_summary`,
`conversation_turns`, `services/llm/*`, `services/conversation/*`, `services/tts/*` or
`practice_languages`.

---

## 11. UI and E2E contracts

| Screen | Primary action | Secondary | Accessibility |
|---|---|---|---|
| Podcasts (`/podcasts`) | Choose a show card | Favourite toggle per card; **Find a new show**; Generate; Surprise me | **My shows** is a labelled section, shown only when non-empty. Cards are groups: the choose button is named by the title and described by its details, including "Episode 2 next" or "Episode 1 unfinished". The favourite toggle is a separate button, `aria-pressed`, named "Favourite Big Little Questions". Suggestions arrive in an `aria-live="polite"` region |
| Setup, series | **Continue episode N** if unfinished, otherwise **Start episode N** | One-off choice tile; per host: ▶ sample and **Recast…**; "What the hosts remember" disclosure with **Start over** | Series hosts are read-only text, with no Shuffle and no personality control. Recast and Start over use `ConfirmDialog` (`role="alertdialog"`, focus trapped and returned, Escape cancels). A name clash is a `role="status"` hint linked to the name field |
| Setup, one-off or series episode 1 | **Start episode 1** / **Start one-off episode** | 007's Shuffle and personality control (now `ThemedSelect`) | As 007 |
| Episode | Unchanged | Unchanged | The header names the episode ("Episode 2" or "One-off") |
| Every drop-down | n/a | n/a | `ThemedSelect` follows the APG select-only combobox. Options use theme tokens; the selected option is marked with colour and a check; the focused option has an outline; contrast ≥ 4.5:1 (FR-021) |

New shared components:
- `ThemedSelect`;
- `ConfirmDialog`.

New podcast components:
- `FavouriteToggle`;
- `MyShows`;
- `FindNewShow`;
- `SeriesHosts`;
- `SeriesHostCard`;
- `RecastDialog`;
- `RememberedPoints`;
- `EpisodeKindFieldset`;
- `ContinueEpisode`.

New hooks:
- `useFavourite`;
- `useSeries`;
- `useShowDiscovery`;
- `useRecast`.

**Setup routes**:
- `/podcasts/setup?show=<template_id>` (007);
- `/podcasts/setup?saved=<saved_show_id>` (new: a kept learner-made show);
- router-state drafts (007), now also used for suggestions.

**E2E specs** (`frontend/e2e/`), all API calls mocked through `page.route()`:
- `podcast-series.spec.ts` (new):
  - series card badge and Start episode 2;
  - read-only hosts;
  - Recast confirm and cancel;
  - Continue unfinished;
  - one-off choice;
  - remembered points and Start over;
  - name-clash hint;
  - the episode header number.
- `podcast-favourites.spec.ts` (new):
  - favourite and unfavourite;
  - the My shows group appears and hides;
  - a series show stays after unfavouriting;
  - reload persistence (mocked).
- `podcast-discovery.spec.ts` (new):
  - Find a new show;
  - another set with `avoid_titles` sent;
  - favourite a suggestion;
  - start a suggestion;
  - the plain error message;
  - the ready-made list unchanged.
- `themed-select.spec.ts` (new): every drop-down (setup personality, Settings, the level control,
  the flashcard word filter, the provider fields), opened in light, dark and system-dark themes:
  - option background and text equal the theme tokens;
  - computed contrast ≥ 4.5:1 for normal, selected and focused options;
  - the focused option differs visibly from the others;
  - keyboard navigation.
- Existing specs that pick a value from these drop-downs switch to `chooseOption()`:
  `settings`, `conversation-level`, `practice-language`, `flashcards`, `podcasts`.
- `fixtures.ts` gains:
  - `showListingFixture`, `seriesSummaryFixture`, `seriesDetailFixture`, `suggestionsFixture`;
  - `chooseOption(page, label, optionName)`;
  - `contrastRatio(foreground, background)`.
