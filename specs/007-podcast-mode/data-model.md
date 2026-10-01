# Data Model: Podcast Mode

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Research**: [research.md](research.md)

This feature adds **five tables** and **one column**, and rewrites no existing row. An episode is an
ordinary conversation (research R1): the new tables only record what is podcast-specific about it.
Everything else is fixed, in-code catalogue data.

---

## 1. In-code catalogues

### 1.1 `PodcastFormat` (`backend/app/podcasts/catalog.py`)

Frozen, slotted dataclass. `PODCAST_FORMATS: Mapping[str, PodcastFormat]` holds the entries in
display order. `DEFAULT_PODCAST_FORMAT = "one_host"` (FR-005).

| `format_id` | `label` | `host_count` | `is_learner_speaking` | `has_jump_in` | `max_host_run` | `invite_deadline` |
|---|---|---|---|---|---|---|
| `one_host` | One host | 1 | true | false | — | 1 |
| `panel` | Panel | 2 | true | true | 3 | 4 |
| `listen` | Listen | 2 | false | false | 3 | — |

- `invite_deadline` is the host line, counted since the learner last spoke or passed, that must
  invite the learner (FR-014). It is `None` when the learner does not speak.
- `max_host_run` is the most lines one host may speak in a row (FR-015). It is `None` with one
  host.
- `host_count + (1 if is_learner_speaking else 0) ≤ MAX_PARTICIPANTS = 3` (FR-004).

### 1.2 `EpisodeLength`

| `length_id` | `label` | `target_host_lines` |
|---|---|---|
| `short` | Short | 10 |
| `medium` | Medium (default) | 20 |
| `long` | Long | 40 |

### 1.3 `Personality`

Ten entries (FR-006, research R8), each with:

| Field | Purpose |
|---|---|
| `personality_id` | `enthusiast`, `dry_sceptic`, `storyteller`, `curious_interviewer`, `expert`, `joker`, `warm_mentor`, `contrarian`, `dreamer`, `pragmatist` |
| `label` | Learner-facing, e.g. "Dry sceptic" |
| `description` | One learner-facing line |
| `speaking_style` | Prompt-facing: how a host with it speaks and reacts (English) |

### 1.4 `ShowTemplate` (ready-made shows)

Eight entries (FR-002). The fields are `show_id`, `title`, `premise` and `topic`, all English
interface text, plus `learner_role` (`guest`, `co_host` or `caller`) and
`default_personalities: tuple[str, str]` for the lead and second host. Names and voices are **not**
part of the template: they are cast per language (§1.6).

### 1.5 `PracticeLanguage` (extended, `backend/app/practice_languages/catalog.py`)

There are three new fields. Language data may only appear in this catalogue
(`test_no_language_literals.py`):

| Field | Type | Example (German) |
|---|---|---|
| `host_names` | `Mapping[str, tuple[str, ...]]` keyed by voice gender | `{"female": ("Lena", "Anna", "Sophie", …), "male": ("Jonas", "Felix", "Lukas", …)}` |
| `guest_labels` | `tuple[str, ...]` | `("Gast", "Zuhörer", "Anrufer")` |
| `sample_line` | `str` with `{name}` | `"Hallo, ich bin {name}. Willkommen zur Sendung!"` |

### 1.6 Catalogue invariants (unit tests)

| # | Invariant |
|---|---|
| P1 | Format, length, personality and show ids are unique within their catalogue |
| P2 | `len(PERSONALITIES) ≥ 8` and `len(SHOW_TEMPLATES) ≥ 6` |
| P3 | Every show's two default personalities exist and differ |
| P4 | Every format satisfies the participant bound and the `None` rules in §1.1 |
| P5 | `DEFAULT_PODCAST_FORMAT` and the default length exist |
| P6 | Every practice language has ≥ 8 names for each gender of its installed-catalogue voices, all distinct |
| P7 | Every `sample_line` contains exactly one `{name}` |

---

## 2. Tables

All new tables are created by `create_all()` (research R18). Foreign keys cascade on delete from
`conversations`, so the core tables never depend on these.

### 2.1 `podcast_episodes`: one row per episode

| Column | Type | Notes |
|---|---|---|
| `conversation_id` | INTEGER PK, FK → `conversations.id` ON DELETE CASCADE | 1:1 with the conversation |
| `show_source` | VARCHAR(12) NOT NULL | `ready_made`, `generated` or `surprise` |
| `show_id` | VARCHAR(100) NULL | The ready-made template id; NULL for generated shows |
| `premise` | TEXT NOT NULL | |
| `topic` | VARCHAR(200) NOT NULL | |
| `learner_role` | VARCHAR(12) NOT NULL | `guest`, `co_host` or `caller` |
| `format` | VARCHAR(12) NOT NULL | A `PODCAST_FORMATS` key; fixed for the episode's life |
| `length` | VARCHAR(8) NOT NULL | A length id; fixed for the episode's life |
| `learner_name` | VARCHAR(40) NULL | What the hosts call the learner; NULL means "our guest" (FR-011) |
| `created_at` | DATETIME NOT NULL | |

- The show title is `conversations.scenario_title`, and the language is
  `conversations.target_language`. Neither is duplicated here.
- `conversations.scenario_id` is `PODCAST_SCENARIO_ID = "podcast"` for every episode.

### 2.2 `podcast_hosts`: the hosts of one episode

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `conversation_id` | INTEGER NOT NULL, FK → `podcast_episodes.conversation_id` ON DELETE CASCADE | indexed |
| `slot` | VARCHAR(8) NOT NULL | `lead` or `second` |
| `name` | VARCHAR(40) NOT NULL | |
| `personality` | VARCHAR(30) NOT NULL | A personality id |
| `voice_key` | VARCHAR(200) NOT NULL | Fixed for the episode's life (FR-009) |
| `show_role` | VARCHAR(20) NOT NULL | `host`, `co_host` or `guest_expert` |
| `angle` | TEXT NULL | The host's angle on the topic; generated shows only |

- `UNIQUE(conversation_id, slot)` and `UNIQUE(conversation_id, name)`.
- Only the hosts who take part are stored: One host stores the lead only (FR-003).
- There are no updates after creation (FR-009).

### 2.3 `podcast_host_lines`: one row per host line

| Column | Type | Notes |
|---|---|---|
| `message_id` | INTEGER PK, FK → `messages.id` ON DELETE CASCADE | The line's text is the message's `content` |
| `conversation_id` | INTEGER NOT NULL, FK → `podcast_episodes.conversation_id` ON DELETE CASCADE | indexed |
| `host_id` | INTEGER NOT NULL, FK → `podcast_hosts.id` | Exactly one speaker (FR-012) |
| `intent` | VARCHAR(10) NOT NULL | `open`, `greet`, `discuss`, `wrap_up` or `sign_off` |
| `invites_learner` | BOOLEAN NOT NULL DEFAULT FALSE | Set by the policy, never parsed from text |
| `is_passed` | BOOLEAN NOT NULL DEFAULT FALSE | The learner passed on this invitation (FR-017) |
| `is_revealed` | BOOLEAN NOT NULL DEFAULT FALSE | Listen: the learner tapped it (FR-043) |
| `was_trimmed` | BOOLEAN NOT NULL DEFAULT FALSE | The sanitiser removed text (research R4); for SC-003 audits |

- Learner lines have **no row**. A `messages` row with `role = 'user'` in an episode is the learner.
- An episode's **lines** are its messages in `created_at` order, joined to this table.

### 2.4 `podcast_preferences`: single row, `id = 1`

| Column | Type | Default | Notes |
|---|---|---|---|
| `id` | INTEGER PK | 1 | |
| `last_format` | VARCHAR(12) NOT NULL | `one_host` | Written when an episode starts (FR-005) |
| `is_show_text_on` | BOOLEAN NOT NULL | FALSE | Listen's Show text switch (FR-043) |
| `interests` | TEXT NOT NULL | `'[]'` | A JSON array of up to 10 strings, each 1–40 characters after trimming, with no case-insensitive duplicates (FR-023) |
| `learner_name` | VARCHAR(40) NULL | NULL | Remembered for the next setup screen (FR-011) |
| `updated_at` | DATETIME NOT NULL | now | |

The row is created with its defaults on first read, as `app_settings` is.

### 2.5 `conversation_summaries`: the latest summary of each conversation

Owned by `app/conversation_summary/`.

| Column | Type | Notes |
|---|---|---|
| `conversation_id` | INTEGER PK, FK → `conversations.id` ON DELETE CASCADE | |
| `up_to_message_id` | INTEGER NOT NULL | The last message the summary covers |
| `level` | VARCHAR(12) NOT NULL | The conversation level it was written at |
| `points` | TEXT NOT NULL | A JSON array of 1–5 `{conversation_language, english}` pairs |
| `created_at` | DATETIME NOT NULL | |

A cache hit requires `up_to_message_id` to equal the conversation's last message id, and `level`
to equal the current level. Otherwise the summary is regenerated and the row replaced (FR-042).

### 2.6 `app_settings` (one new column)

| Column | Definition | Notes |
|---|---|---|
| `summary_language` | `VARCHAR(12) NOT NULL DEFAULT 'conversation'` | `conversation` or `native` (FR-040). Added through `_ADDITIVE_COLUMNS` |

`AppSettingsRecord` gains `summary_language: str = DEFAULT_SUMMARY_LANGUAGE`.

---

## 3. Domain value objects (`backend/app/podcasts/services/`)

| Object | Fields | Invariants |
|---|---|---|
| `Host` | `slot`, `name`, `personality_id`, `voice_key`, `show_role`, `angle` | Non-empty name ≤ 40 characters; a catalogued personality |
| `Cast` | `lead: Host`, `second: Host | None` | `second` is None exactly when the format has one host. Two hosts differ in name, in personality, and in voice unless only one voice is installed (FR-007). No host has the learner's name |
| `ShowDraft` | `source`, `show_id`, `title`, `premise`, `topic`, `learner_role`, `language`, `lead`, `second` | Always two hosts (the format picks who takes part, FR-003). Validated again on episode creation, because it comes from the client |
| `LineFacts` | `speaker` (a host slot or `LEARNER`), `intent`, `invites_learner`, `is_passed`, `text` | Built from stored lines only |
| `LineCue` | `speaker_slot`, `intent`, `invites_learner`, `is_after_pass`, `is_settle_invite` | Output of `TurnPolicy.next_cue()` |
| `EpisodeState` | `format`, `length`, `cast`, `lines: tuple[LineFacts, ...]`, `is_finished` | Input to `TurnPolicy` |

---

## 4. Turn state (derived, never stored)

`TurnPolicy.turn(state)` returns one of:

| `turn` | `awaiting` | When |
|---|---|---|
| `hosts` | `opening` | There are no lines yet |
| `hosts` | `reply` | The last line is the learner's |
| `hosts` | `continue` | The last line is a host line that does not invite, or whose invitation was passed |
| `learner` | — | The last line is a host line with `invites_learner` and not `is_passed` |
| `finished` | — | The conversation's status is `completed` |

State transitions:

```text
            ┌──────── /next (Continue) ────────┐
            ▼                                  │
 opening ─/next─► hosts:continue ──/next──► (line invites?) ──yes──► learner
                     ▲                                             │  │  │
                     │                        /message (reply) ◄───┘  │  │
                     │                         │                      │  │
                     │   hosts:reply ◄─────────┘   /pass (Panel) ─────┘  │
                     │      │ /next (auto)             │                  │
                     └──────┴──────────────────────────┘                  │
   any non-finished state ── /end ──► sign-off line ──► finished ◄─ Listen sign-off
```

- `/message` is accepted at `learner`, at `hosts:reply` (adding to the learner's own turn, as in
  roleplay), and at `hosts:continue` only when the format `has_jump_in` (FR-017).
- It is refused with 409 in Listen and when the episode is finished.
- `/pass` is accepted only at `learner` in a format with `has_jump_in`.

---

## 5. Turn policy rules (pure, `turn_policy.py`)

Given `EpisodeState` and an injected `random.Random`, `next_cue()` applies these rules in order:

1. **Intent**:
   - no lines → `open` (lead);
   - Panel or Listen with exactly one host line → `greet` (second);
   - an End request → `sign_off`;
   - host lines ≥ target and no `wrap_up` yet → `wrap_up`;
   - Listen, when the last line is a `wrap_up` → `sign_off`;
   - otherwise → `discuss`.
2. **Speaker**, with the first applicable rule winning:
   1. a host with `max_host_run` lines in a row is excluded;
   2. the host named by the learner's last line, if that line was the last one;
   3. if the hosts' line counts differ by ≥ 2, the host with fewer lines;
   4. the host named in the last host line, other than its speaker;
   5. `sign_off` and `open` prefer the lead;
   6. otherwise the other host with p = 0.7, the same host with p = 0.3. After a learner line, the
      host who invited them with p = 0.6.
3. **Invitation** (`invites_learner`), in speaking formats only:
   - One host → always, except `sign_off`;
   - Panel → with `run` = host lines since the learner last spoke or passed (this one included), the
     hazard is 0.25, 0.45, 0.6, and then certain at `run = invite_deadline`;
   - `wrap_up` → always (the learner's closing words);
   - `sign_off` → never.
4. **Settle invite**: an invitation whose two previous lines came from different hosts asks the
   learner to settle it (US3).

**Guarantees**, as property tests over ≥ 1,000 seeded simulated episodes for each format:
- the invitation deadline is never exceeded (FR-014);
- no run is longer than `max_host_run` (FR-015);
- each host has at least 25% of host lines in every episode with ≥ 8 host lines (FR-015; see plan
  interpretation 2);
- an addressed host always speaks next (FR-018);
- the wrap-up comes within 2 host lines of the target (FR-019);
- Listen always ends with `sign_off`.

---

## 6. Validation rules at the boundary

| Input | Rule | Failure |
|---|---|---|
| Generator idea | 1–200 characters after trimming | 422, "Type a few words about the show you'd like, or press Surprise me." |
| Interests | ≤ 10 items, each 1–40 characters after trimming, no case-insensitive duplicates | 422 naming the problem |
| Learner name | 1–40 characters after trimming, or null | 422 |
| `ShowDraft` on episode start | Catalogued personalities; both voices belong to the practice language; names distinct and not the learner's; `learner_role` valid | 422 naming the host and field |
| Format and length | Catalogue ids | 422 via pattern |
| `summary_language` | `conversation` or `native` | 422 via pattern |
