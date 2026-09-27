# Validation record (006)

What was checked, how, and what was not. Benchmark figures are in
[benchmark-results.md](benchmark-results.md).

## Accessibility (T104)

A human screen-reader pass was **not** done in this session. Instead a throwaway Playwright audit
measured the same properties in Chromium, in the light and dark themes:

| Check | Light | Dark |
|---|---|---|
| Practice-language radios: group named "Practice language"; ArrowDown moves Spanish → German | pass | pass |
| Radio card target height | 48 px | 48 px |
| Settings hint contrast (fieldset and "Not installed" hint) | 4.56:1 | 4.56:1 |
| "Not installed" hint is `role="status"` and linked by `aria-describedby` to the Voice select | pass | pass |
| Home note text / name / link contrast | 4.56 / 16.62 / 4.56 | 6.28 / 15.99 / 6.28 |
| Home link: underlined (not colour alone) | pass | pass |
| Past Chats language tag contrast; tag is part of the row's accessible name | 4.80:1 | 5.70:1 |
| Chat voice notice is `role="status"`, contrast | 4.80:1 | 5.70:1 |
| Chat header tag announced as "Conversation language: German", contrast | 4.80:1 | 5.70:1 |

One fix came out of it: the Home "Change in Settings" link was 21 px tall; it now has a 44 px
minimum target.

## Quickstart walkthrough (T105)

Scripted against the **real stack** (Ollama `llama3.1:8b`, Piper, faster-whisper `medium` from the
learner's settings) on a **copy of the learner's pre-006 database** (38 conversations, 302 messages,
27 words, 2 decks, 8 sessions), with an isolated `HOME`. The learner's own database, settings and
network were not touched. Checks are by API, not by clicking through the UI; the UI paths are
covered by the Playwright suite.

| Step | Check | Result |
|---|---|---|
| §2 | Catalogue, voices, German selects Thorsten, Spanish voice under German is 422, `?language=` required | pass (6/6) |
| §4.1 | Settings → first German greeting (SC-001, API time only, no UI) | pass, 0.8 s |
| §4.1 | Greeting is German; conversation is German; spoken by Thorsten | pass |
| §4.2 | Dictation keeps "hätte" and "Stück" | **fail**: "Stück" heard as "Steck" (Kerstin-synthesised audio; the SC-003 open item) |
| §4.3 | Translation, phrasing, word lookup, suggestions, helper | pass; German side German, explanations English |
| §4.4 | "Ich habe gestern nach Berlin gefahren." is corrected | see below |
| §4.4 | "Grüß Gott!" and "Servus, wie geht's?" are not flagged | pass |
| §4.5 | Beginner reply is German | pass (27 words: the 005 Beginner length gap still applies) |
| §4.6 | English input is answered in German, asking for German | pass |
| §4.7 | Only the three German words listed; German deck; word in German voice; analytics German-only | pass |
| §4.8 | Spanish voice is the pre-upgrade choice; Spanish words (27) and decks (2) only; Past Chats label both | pass |
| §4.8 | An old Spanish conversation continues in Spanish, and stays Spanish after switching to German | pass |
| SC-005 | Pre-006 columns of pre-006 rows in conversations, messages, vocabulary_items, decks, practice_sessions, card_results | **unchanged**; old decks and sessions read `es`; Spanish voice seeded |
| §4.9 | A Spanish session finished while German is selected counts under Spanish only | pass |
| §4.10 | "Hotel" saved from a German and a Spanish conversation is two words | pass |
| §5 FR-018 | German voice files absent: catalogue and Settings flag it; chat text works; message and word audio are a plain 503 with the German message; nothing synthesised; one warning logged | pass |

**§4.4, corrections in German.** Gentle mode never shows a note (a Gentle correction is the reply's
recast, by 003's design), so the quickstart's wording was wrong and has been corrected to Strict.
In Strict, German corrections fire, but on `llama3.1:8b` they are unreliable in the same way 003
recorded for Spanish: across six tries, "Ich haben heute Hunger" and "Er gehen morgen ins Kino" got
right fixes alongside wrong ones ("Hungrig", "zum Kino"), and "…nach Berlin gefahren" got "zu",
"gegangen" or "gesternabends", never "bin". Corrections stay marked experimental.

**Not done in this session**:
- SC-007 (offline): the network was not disconnected. Every provider in the German path is local
  (Ollama, Piper, faster-whisper), and the German voices are on disk.
- SC-003 with a human voice, and listening to replies by ear.
- The walkthrough with Claude selected. One live German turn through Claude passed (T069).
- A human screen-reader pass (see Accessibility above).
