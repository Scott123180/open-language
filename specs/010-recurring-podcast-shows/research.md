# Research: Recurring Podcast Shows

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Date**: 2026-10-17

Each entry records a decision, why it was made, and what else was considered. The spec has no
NEEDS CLARIFICATION markers; its one clarification (FR-022) is folded in. These entries settle the
design questions raised by reading the code on `010-recurring-podcast-shows` @ `335baa8`.

Four findings shape the whole design:

1. **An episode is already self-contained.** `podcast_hosts` copies the hosts into each episode,
   and the history the engine sees is rebuilt from stored facts (007 R3). So a series is an
   addition *beside* episodes, not a change to them: a series hands an episode its hosts and its
   memory when the episode starts, and the episode then runs exactly as in 007 (R2, R5).
2. **The standing prompt must not change during an episode.** The engine rebuilds a session when
   the prompt's fingerprint changes, and `render_cue` must re-render every cue byte for byte
   (007 R3). Memory that grows while an episode runs would break both. So each series episode
   stores a **snapshot** of what the hosts remember, taken when it starts (R5).
3. **Nothing in the app can delete a conversation today.** The spec's "episode deleted from Past
   Chats" edge case is honoured by construction (every new row cascades from `conversations`),
   with no new delete feature (R3).
4. **A native `<select>` popup is drawn by the browser and the OS, not by the page.** 007 already
   set `color-scheme` and `option` colours (`097fcc7`), and the learner still sees an off-theme
   list. Playwright cannot see a native popup either, so SC-008 cannot be automated against one.
   The fix is an in-app listbox (R11).

---

## R1. Where a show's learner state lives: one `podcast_shows` table, created lazily

**Decision**: One new table, `podcast_shows`, holds every show the learner has state for:
- a **ready-made** show gets a row (with `template_id` set and no content columns) the first time
  it is favourited or a series of it starts. Its title, premise, topic, role and default
  personalities are always read from `SHOW_TEMPLATES`, never copied;
- a **learner-made** show (generated, surprise or suggested) gets a row, with its content
  (title, premise, topic, role, both personalities and angles), when it is *kept*: favourited or
  played (FR-014, FR-019).

Favourite is a nullable `favourited_at` on that row, so it is language-independent by construction
(spec edge case "favourited in one language"). Series point at `podcast_shows.id`.

The API keeps naming a ready-made show by its template id (`show_id`, as in 007) and adds
`saved_show_id` for a learner-made show. One resolver, `ShowLibrary.keep(draft)`, turns a draft
into a row (get-or-create for a template, look-up or create for a learner-made draft).

**Rationale**: Favourites, series and "kept" shows all need one foreign-key target that covers
both kinds of show. Creating ready-made rows lazily means the catalogue in code stays the only
source of a ready-made show's content, and nothing is seeded or synchronised at start-up.

**Alternatives considered**:
- *Seed a row per ready-made show in `init_db`*: a catalogue edit would need a sync step, and a
  removed show would leave an orphan.
- *A polymorphic key string (`ready_made:big-little-questions`, `saved:12`)*: one parser, but every
  table would carry an unenforced reference; a foreign key needs a real row.
- *Separate tables for ready-made favourites and saved shows*: two of everything (favourites,
  series foreign keys, My shows queries) for one concept.

---

## R2. A series is a show in one language, with its own hosts

**Decision**: `podcast_series` is one row per (show, practice language), unique on that pair, and
created by the first series episode (spec Key Entities). Its hosts live in `podcast_series_hosts`,
one row per slot, **always both slots**, even when the episode format uses one host (spec edge
case "format differs between episodes"). Each row records `joined_after_episodes`: 0 for the
original hosts, or the episode count at the moment a host was recast (FR-009).

Starting a series episode copies the series' hosts **for the format's slots** into `podcast_hosts`,
exactly as 007's `_participating_hosts` does with a draft. Everything downstream (cues, sanitiser,
voices, summary, Past Chats) keeps reading the episode's own hosts.

**The first episode fixes the hosts**: the series is created from the draft the learner started
with, after any Shuffle or personality change (FR-008: the first episode keeps today's controls).
**Later episodes** must start with the series' hosts. The draft the client sends is compared slot
by slot (name, personality, voice); a mismatch is a plain 409 ("This show's hosts changed. Open
the show again.") rather than a silent override (SC-001 by construction).

**Rationale**: Copying into `podcast_hosts` leaves the 007 episode pipeline untouched, so no
existing episode code needs to know about series. Checking rather than ignoring the client's hosts
keeps the request honest: a stale tab after a recast in another tab is told, not overruled.

**Alternatives considered**:
- *Episodes point at series hosts instead of copying them*: a recast would rewrite the hosts of
  past episodes, and Past Chats would show the wrong names.
- *A separate "start series episode" endpoint with no hosts in the body*: one endpoint fewer to
  mismatch, but two ways to start an episode, and the first series episode would still need the
  draft. `POST /episodes` with `kind` keeps one start path (contracts §4).

---

## R3. Linking episodes to a series: a link table, numbers stored at start

**Decision**: `podcast_series_episodes` holds one row per series episode: `conversation_id`
(primary key, cascading from `podcast_episodes`), `series_id` (cascading from the series),
`episode_number`, the memory `snapshot` (R5), and `remembered_up_to_message_id` (R6).

- **Episode count** is the number of link rows; the **next episode number** is count + 1.
- **One-off episodes have no link row**, so they cannot read from or add to a series (FR-007).
- **Pre-feature episodes have no link row**, so every show starts a fresh series numbered 1
  (FR-022), with no data migration.
- **Reset** deletes the series row. Its hosts, links and memories cascade away; the episodes and
  their conversations stay in Past Chats (FR-011).
- **An abandoned episode** keeps its link row, so it counts (spec edge case).
- **A deleted conversation** (no UI does this today) cascades its link row and the memories drawn
  from it (spec edge case). The count follows; stored numbers are labels for the prompt and the
  header, never used to compute the next one.

**Rationale**: A link table is additive (`create_all()`), needs no `ALTER TABLE` with a foreign
key on SQLite, and makes FR-007 and FR-022 hold by construction rather than by a flag that every
query must remember to check.

**Alternatives considered**:
- *Two new columns on `podcast_episodes` (`series_id`, `episode_number`)*: an added column cannot
  carry `ON DELETE CASCADE` through `_add_column_if_missing`, so reset would have to update rows
  instead of deleting one.
- *Derive the number by rank on every read*: the prompt snapshot needs a fixed number, so the
  number is stored anyway.

---

## R4. What a series episode is offered: continue first, then next, then one-off

**Decision**: A show's **series summary** (contracts §1) carries `episode_count`,
`next_episode_number` and `unfinished_episode`: the latest linked episode whose conversation is
still `active`, if any. The setup screen then offers, as its one primary action:
1. **Continue episode N** when an episode is unfinished (FR-002, US1-5). Starting a new episode is
   a secondary text button below it;
2. otherwise **Start episode N** (the series is the default choice);
3. **One-off episode** is a secondary choice tile beside it (FR-002, US2-1).

Starting a new episode while one is unfinished leaves the unfinished one counted and still
resumable from Past Chats; it is not closed.

**Rationale**: It keeps Principle IV's single primary action on a screen that now has three
possible starts, and it matches the order the spec gives (continue, next, one-off).

**Alternatives considered**: *Three equal buttons*: violates the single-primary-action rule. *Close
the unfinished episode when a new one starts*: loses lines the learner may come back to.

---

## R5. Memory reaches the model as a snapshot, taken when the episode starts

**Decision**: When a series episode starts, the series' remembered points (bounded, R7) and the
episode's facts are frozen into the link row's `snapshot` as JSON:
- `episode_number`;
- `topics_covered`: the subjects of earlier episodes;
- `about_learner`: what the learner shared;
- `new_host_slots`: the slots whose host joins the series in this episode (recast).

The points are stored in the conversation's language version (R6). Two prompt pieces are rendered
from the snapshot, never from live memory:
- a **series section** in the standing prompt (`build_standing_prompt(..., series=brief)`). It says
  this is episode N of a continuing show, lists the topics covered and what the learner has said,
  and tells the hosts to refer back where it fits, to choose a subject not in the list, never to
  claim to remember anything beyond the list, and to introduce any new host as new to the show;
- **series variants of the `open` and `greet` cues**: welcome the learner back by name, say the
  show is continuing, and bring up one remembered point (US1, FR-005). A new host's greet
  introduces them as new to the show (US3-3).

A one-off episode has no snapshot. Its standing prompt and cues are **byte-identical to 007's**,
which a unit test pins (FR-007).

**Rationale**: The engine fingerprints the standing prompt and rebuilds the session when it
changes, and `render_cue` must reproduce every cue from stored facts (007 R3). Memory that grew
mid-episode (a catch-up finishing during it, R6) would rebuild the session for no reason and
change the history under it. A snapshot makes an episode reproducible: resuming it next week
gives the model exactly what it had when it began. Putting the recall in the opening cue, not
only in the standing rules, gives the small local model one concrete moment to do it, which is
what SC-002 measures.

**Alternatives considered**:
- *Read memory live on each line*: breaks the fingerprint and re-rendering (above).
- *Add a `recall` intent to the turn policy, placed mid-episode*: one more policy rule and cue
  for a behaviour the opening already covers. It can be added later if SC-002 is missed.
- *Pass the previous episode's transcript*: unbounded (FR-006) and slow (SC-006).

---

## R6. Memory is written by a background catch-up; a series Start waits for it, visibly

**Decision**: A `SeriesMemoryKeeper` turns finished or abandoned lines into remembered points with
**one structured call per episode chunk**, through the stateless `StructuredLLMProvider`, as the
summariser does (007 R13). It runs in a background thread with its own database session, at two
moments:
1. **after the sign-off line of a series episode is stored**. `EpisodeTurns` reports the finish
   through a one-method interface, `EpisodeEndings`, which the factory wires to the keeper (DIP),
   so the turn code never imports the memory code;
2. **when the setup screen opens a series**, through `POST /series/{id}/memory` (202, like 007's
   warm-session endpoint). This catches abandoned episodes, which have no sign-off.

The keeper's input and output:
- **Progress**: the keeper reads only lines after the link row's `remembered_up_to_message_id` and
  moves the marker forward. An episode abandoned, remembered, then resumed is only re-read from
  where it stopped.
- **Threshold**: an episode with fewer than 2 lines is skipped until it has more.
- **Reply**: `{topic, about_learner[≤3]}`, each point in two versions, the conversation's language
  and English, as the summary does. The learner sees the English version; the snapshot carries
  the conversation-language version (R5).
- **Grounding rule, enforced in code**: learner points are kept only from a chunk that contains
  learner lines. A Listen episode can therefore add topics but never facts about the learner
  (spec edge case), and the model cannot attribute a host's words to the learner across a chunk
  with no learner lines.
- **Duplicates**: the points already remembered are given to the model as "already remembered",
  and it is told not to repeat them. A re-read episode's topic replaces its earlier topic point.
- **Chunks**: long episodes are folded in chunks of at most 6,000 characters, the summariser's
  budget (007 R14).

Concurrency: one catch-up per series at a time (a per-series in-process guard, like
`EpisodeLocks`). A second request while one runs returns `{"status": "running"}`.

Provider: `MemoryCatchUps` is one process-wide instance, because the guard must outlive a request,
but it holds no keeper or provider. Every `start` and `wait` is handed a `SeriesMemoryKeeper` built
for that request from `get_structured_llm`, which reads the learner's current selection. A provider
switched on Settings (004, no restart) therefore applies to the next catch-up, and a catch-up
already running finishes with the provider that was selected when it started (Principle VI).

**Start waits for memory, and says so** (spec clarification, 2026-10-17). The series detail
reports `memory_status`:
- `up_to_date`: no episode has unread lines;
- `pending`: lines are unread and no catch-up is running;
- `running`: a catch-up is running.

When the learner presses **Start episode N** (or **Continue**) and the status is not
`up_to_date`, the setup screen:
1. keeps the Start button in a busy state;
2. shows a `role="status"` message: "Hugo and Inés are catching up on episode 3. This takes a
   few seconds.";
3. calls `POST /series/{id}/memory?wait=true`. The server starts a catch-up if none is running,
   then holds the request until it finishes or `MEMORY_WAIT_SECONDS` (30 s) pass. It waits on the
   catch-up's completion event in an executor, so the event loop is never blocked;
4. on `up_to_date`, starts the episode with no further action. The new snapshot then includes
   the last episode.

If the catch-up fails (provider error) or times out:
- the message changes to "The hosts couldn't catch up on episode 3. {provider message or 'It's
  taking longer than usual.'}";
- it offers **Try again** (primary) and **Start without it** (secondary): the episode starts
  with what is already remembered;
- nothing switches provider (Principle VI), and starting without the update is the learner's
  explicit choice, never a silent one.

`POST /episodes` itself does not wait or refuse: the client does the waiting, so the start
endpoint keeps one job and stays fast. Two tabs racing to start is harmless: the second takes
whatever memory exists at that moment.

**Rationale**:
- Recall is the point of a series (US1). Waiting a few seconds with a clear message is better
  than an episode that has forgotten the last one, and this is the learner's stated preference.
- In the usual case the status is already `up_to_date` and nothing waits. The catch-up after a
  sign-off, or the one started when the setup screen opens, has normally finished before Start
  is pressed. The wait only shows when the learner starts straight after finishing or abandoning
  an episode.
- SC-006 still holds as specified, because it compares the first host line *of the episode*.
  The catch-up is a separate, visible step before the episode exists, with its own budget,
  measured in R12: p90 ≤ 15 s on the local setup.
- A failed catch-up outside a Start (sign-off or setup open) is logged and retried at the next
  trigger. It only reaches the learner when they are waiting on it.

**Alternatives considered**:
- *Never wait: start with what is remembered and let late points arrive for the next episode*:
  fastest, but an episode started straight after the last one could forget it entirely. The
  learner chose to wait.
- *Make `POST /episodes` itself wait*: one call fewer, but a start request that can block for
  30 s, and no distinct "catching up" state to show or retry.
- *Extract at Start, synchronously, always*: simplest, but adds a model call (5–10 s locally) to
  every later episode's start, even when memory is already up to date.
- *Extract after each learner line*: competes with host-line generation on a single local GPU, on
  the latency path 007 protects (SC-009 of 007).
- *Reuse the conversation Summary*: it summarises what was said (five points, both speakers). It
  is not about the learner, it is cached per level, and folding its points into memory would
  carry the hosts' claims as if the learner had made them.

---

## R7. Memory stays bounded: newest points win, within fixed caps

**Decision**: Each series remembers at most **10 topics covered** and **8 things about the
learner**, each point at most 160 characters, and the conversation-language text of all of a
series' points together is at most **1,200 characters** (`REMEMBERED_TEXT_BUDGET`). When a write
would exceed a cap, the oldest points of that kind are deleted; then, while the total text is over
the budget, the oldest point of either kind is deleted. Both happen in the same transaction as
the write. The caps alone would allow 2,880 characters, which the prompt section could not hold;
enforcing the budget at write time means the renderer never drops anything, so what is stored is
exactly what is remembered, shown and sent (FR-011), with no hidden archive. A unit test bounds
the rendered series section at **1,800 characters** for any stored set within the budget,
whatever the number of episodes (FR-006, SC-006).

Because the topics are bounded too, "a topic not already covered" means a topic not among the
remembered ones (FR-005 as amended). From roughly the eleventh episode, a topic from the earliest
episodes may come back.

**Rationale**: Recency is a cheap, predictable proxy for "most useful", and the learner can see
and reset the list. A fixed cap makes FR-006 a property of the code rather than of the model.
The 1,200-character budget is roughly 300–400 tokens of extra prompt. At local prefill
speeds that costs well under a second, which SC-006's benchmark measures (quickstart §3).

**Alternatives considered**: *Ask the model to consolidate the list after each episode*: one more
call, and a small model can merge two true facts into one false one (SC-002's "no invented
memory"). *Score points by how often the hosts used them*: needs per-line attribution of recall,
which nothing measures reliably.

---

## R8. Consistent hosts: no Shuffle after the first episode; Recast is deliberate and immediate

**Decision**:
- **Series episode 1 and one-off episodes** keep 007's Shuffle and personality drop-down (FR-008).
- **Series episodes 2 and later** show each host's name, personality label and voice sample,
  read-only. The secondary action is **Recast…**. It opens a confirmation dialog stating that the
  new host joins without the earlier history (FR-009). The dialog holds an optional personality
  choice ("Any", or one of the personalities the other host does not have).
- **Confirming** calls `POST /series/{id}/hosts/{slot}/recast`, which applies at once to the
  series: `HostCaster.recast` gives the slot a new name, a new personality (the chosen one, or a
  random free one) and a voice by 007's interpretation 6. `recast` gains an optional
  `personality_id` for this; 007's Shuffle calls it without one and is unchanged. The slot's `joined_after_episodes` is
  set to the current count. **Cancelling** sends nothing.
- With two installed voices per language, the recast host usually keeps the slot's voice
  (interpretation 6 of 007). The dialog says so when that is the case.
- A **ready-made show with no series** opens with the hosts on its card every time, as
  `cast_template` already guarantees for a given language and learner name (FR-010). Once a
  series exists, the catalogue lists the show with the series' hosts.
- **Name clash** (spec edge case): series hosts never change name. When the learner's name equals
  a series host's, the setup screen says so beside the name field. Start returns 422 with "Hugo
  has the same name as you. Change the name the hosts call you.", with no Shuffle advice.

**Rationale**: Applying the recast immediately, on the server, means the next episode cannot start
with anyone but the series' hosts (R2's check), and the confirmation is the one place the change
is made. The personality choice inside the dialog spares the learner a chain of confirmed
recasts to reach the personality they want.

**Alternatives considered**: *Recast on the client, sent with Start*: Start would have to accept
changed hosts, defeating R2's check. *Allow free edits of a host who has not appeared yet*: a
second editing mode for one rare moment.

---

## R9. My shows: favourites, series in this language, and played learner-made shows

**Decision**: The catalogue response gains `my_shows`. It holds, for the current practice
language:
- every favourite;
- every show with a series in this language;
- every learner-made show that has been played.

They are ordered by the most recent of `last_played_at` and `favourited_at`. Each entry carries
`is_favourite` and its series summary (R4). The group is hidden when empty (FR-013).

Every show in the response is a `ShowListing`: a `ShowDraftModel` with the extra read-only fields
`saved_show_id`, `is_favourite` and `series`. The client can send a listing straight back as the
draft of `POST /episodes`, since pydantic ignores the extra fields.

Unfavouriting a **learner-made show** that has never been played and has no series deletes its row:
it was kept only by the favourite (FR-019). A ready-made row without a favourite or a series is
also deleted, which keeps `podcast_shows` free of rows that mean nothing.

A played learner-made show would otherwise stay in My shows for ever, and every played Surprise me
show would pile up there. **Remove** (FR-024) is a secondary action on a kept learner-made show's
card in My shows. After a `ConfirmDialog` it calls `DELETE /api/podcasts/shows/{saved_show_id}`,
which deletes the row. The cascade ends its series in every language (hosts, links, memories),
while the episodes stay in Past Chats with `episode_number: null`. Ready-made shows need no Remove,
since unfavouriting and Start over already empty their row.

**Rationale**: US4-3 needs a played generated show to appear in My shows even without a series or
a favourite, because it has nowhere else to live. One response serves the screen, so My shows and
the ready-made list cannot disagree.

**Alternatives considered**: *A separate `GET /my-shows`*: two queries to keep in step on every
favourite change. *Keep every learner-made draft ever generated*: contradicts FR-019.

---

## R10. Find a new show: seeds in code, one structured call, duplicates dropped in code

**Decision**: `POST /api/podcasts/shows/discover {avoid_titles}` returns
`{suggestions: ShowDraftModel[]}` with source `suggested` (a new entry in `SHOW_SOURCES`).
`ShowDiscovery`:
1. **Seeds**: draws 5 distinct (topic, angle) seeds with the existing `SurpriseTopics` vocabulary
   and a fixed quota. With saved interests, 3 of the 5 seeds come from interests, which meets
   US5-4's "most" for the seeds. Without interests, all 5 come from the built-in topics (varied
   everyday topics). The quota governs the seeds, not the response: if filtering drops
   interest-seeded shows, a returned set can hold fewer than 3 that relate to the interests. This
   is accepted, as making it certain would cost extra calls against SC-007's 30 s.
2. **One call**: a single structured call with a schema for an array of 5 shows, each with the 007
   generator's fields and its own `is_suitable` judgement (FR-018). The prompt lists the seeds,
   one show per seed, and the titles to avoid.
3. **Parsing**: each show is parsed with the generator's own parser (refactored to be shared, not
   copied). Unsuitable and unreadable shows are dropped, and so is any whose normalised title
   (casefolded, punctuation stripped) matches a ready-made show, one of the learner's shows, or a
   title in `avoid_titles` (FR-017). The hosts are cast by `HostCaster.cast_personalities`, as for
   generated shows. A duplicate means the same normalised title. A show with a new title and a
   premise close to an existing one is not caught; this is accepted, since judging premise
   similarity would need another model call.
4. **Shortfall**: if fewer than 3 survive, one top-up call is made for the shortfall with fresh
   seeds. If there are still fewer than 3, the response is 503 with a plain message: "Find a new
   show didn't come up with enough shows this time. Please try again." (FR-020). Provider errors
   surface as the provider's own 503 message (004), and there is no fallback.

Nothing is stored (FR-019). The client sends `avoid_titles` as every suggestion title shown this
visit, so a second set repeats neither the first nor the learner's shows (US5-2).

**Rationale**: One call for five shows is faster on a local model than five calls: shared prompt
prefill, and output in the region of 600 tokens. It fits SC-007's 30 s with room for the rare
top-up. Seeds in code give variety that a small model asked for "five different shows" does not,
and the same reasoning made Surprise me code-seeded (007 R9).

**Alternatives considered**: *Five sequential generator calls*: about three times the latency
locally, since Ollama serialises requests. *A larger static catalogue rotated on refresh*:
contradicts the "ready-made list is not expanded" assumption and is not personalised.

---

## R11. The themed drop-down: an in-app select-only combobox for every drop-down

**Decision**: A new shared component, `ThemedSelect` (`frontend/src/components/shared/`),
implements the WAI-ARIA APG **select-only combobox**:
- a `button`-like element with `role="combobox"`, `aria-expanded`, `aria-controls` and
  `aria-activedescendant`, opening a `role="listbox"` of `role="option"` elements;
- keyboard: Enter/Space/Alt+↓ open; ↑/↓/Home/End move; type-ahead; Enter selects; Escape closes
  without change; Tab selects and moves on;
- styling from design tokens only. The list is drawn on `--color-surface` with `--color-text`, the
  selected option is marked with `--color-primary-subtle` / `--color-primary-text` and a check
  mark, and the focused option has a 2px `--color-primary` outline, so focus and selection stay
  distinguishable even on the same option.

It replaces all five native selects (FR-021):
- `HostCard` (podcast personality);
- `SelectField` (Settings);
- `ConversationLevelControl`;
- `WordFilterBar`;
- `LlmProviderFields`.

`SelectField`'s props stay the same, so the Settings screen does not change. The `option` rule in
`index.css` is deleted along with the last native `<option>`.

**Rationale**:
- A native popup's colours, and above all its hover and focus highlight, are drawn by the browser
  and the OS (GTK on Linux), and differ between Chromium and Firefox. 007's `color-scheme` and
  `option` fix did not hold for the learner.
- `appearance: base-select` (customisable select) styles the popup only in Chromium, and leaves
  other browsers on the native list.
- An in-DOM listbox is the only option that is themed in every browser *and* inspectable by
  Playwright, so SC-008's contrast check can be automated in both themes rather than only checked
  by hand.

**Cost, accepted**: the Vitest and Playwright tests that use `selectOptions()` / `selectOption()`
on these five controls are updated to open the combobox and click the option. That covers the
Settings, conversation-level, practice-language, flashcards and podcasts specs, plus the Vitest tests of the five controls. A shared Playwright helper,
`chooseOption(page, label, option)`, in `fixtures.ts` keeps each change to one line.

**Alternatives considered**: *`appearance: base-select` with native fallback*: keeps the native
tests, but leaves the defect wherever Chromium's support is absent and cannot be checked by
Playwright. *A dependency (Headless UI, Radix Select)*: correct, but a new runtime dependency for
one component the app can own in about 150 lines.

---

## R12. Measuring the model-dependent criteria

**Decision**: As in 003, 005, 006 and 007, model behaviour is measured by hand-run tests under the
existing `benchmark` marker, with a review sheet for what needs a person:
- `test_series_recall_benchmark.py` runs 20 scripted two-episode series on the default local
  setup. Each first episode has learner lines with a known fact; each second episode is run to
  10 host lines. It writes `series-review-sheet.md` for SC-002 (refers back correctly, no invented
  memory) and SC-003 (new topic);
- `test_one_off_isolation_benchmark.py`: 20 one-off episodes of shows with a series in progress
  (SC-004). Because a one-off prompt carries no memory, a reference can only be invented. The
  sheet lists any line that mentions "last time", "last episode" or the known facts, for review;
- `test_series_latency_benchmark.py`: the time to episode 1's first line versus episode 10's, on
  the same series with a full memory, 10 runs each (SC-006). It also times the catch-up wait:
  `POST /series/{id}/memory?wait=true` straight after a Medium episode's sign-off, 10 runs, with
  a target of p90 ≤ 15 s (R6);
- `test_discovery_benchmark.py`: 10 requests, each with time to response, count, duplicates and
  suitability (SC-007).

SC-001, SC-005, SC-008 and SC-009 are guaranteed by construction and covered by ordinary tests.

**Rationale**: The local model's recall is the open risk (spec Assumptions). It is measured before
the feature's quality is claimed, and if SC-002 is missed the feature ships labelled experimental,
as 003 and 005 did.

---

## R13. No new per-language data, dependencies or downloads

**Decision**: The series prompt, memory prompt and discovery prompt name languages through
`ConversationLanguages`, as 007 does. Host names come from the existing name banks. So this
feature registers **no** language-kit `Requirement`, and `kit.sh backfill` is not run. There are
no new Python or npm dependencies, and no new voices.

**Rationale**: FR-023 asks for no per-language changes beyond the existing data. The
language-literal guard test already covers `app/podcasts/`, so new modules inside it are checked
automatically.
