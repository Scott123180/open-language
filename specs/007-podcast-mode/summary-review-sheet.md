# Summary Review Sheet (SC-012, SC-013)

**Feature**: [spec.md](spec.md) | **Benchmark**: `backend/tests/integration/conversation_summary/test_summary_benchmark.py`

Fill one row per summary from a run of the summary benchmark on the default local setup
(`llama3.1:8b`), which prints each summary with its conversation. Cover 20 summaries: 10 roleplay
conversations and 10 podcast episodes, across both practice languages, and at least four at a level
below Natural.

**Bars** (spec SC-012, SC-013):
- 0 summaries state something that was not said;
- at least 90% cover every main point the reviewer lists for the conversation;
- in 100% the English and conversation-language versions describe the same points;
- below Natural, the conversation-language version meets the level's limits at least as often as
  roleplay partner replies do (005's measure).

**Status**: not yet run. The session that built 007 had no Ollama, so the rows below are empty.
Record the result in `docs/architecture.md` § "Open items" if a bar is missed.

| # | Kind | Language | Level | Main points the reviewer lists | Invented statements (0?) | Every main point covered? | Same points in both versions? | Level limits met? |
|---|---|---|---|---|---|---|---|---|
| 1 | roleplay | es | natural | | | | | |
| 2 | roleplay | es | natural | | | | | |
| 3 | roleplay | es | beginner | | | | | |
| 4 | roleplay | es | elementary | | | | | |
| 5 | roleplay | es | natural | | | | | |
| 6 | roleplay | de | natural | | | | | |
| 7 | roleplay | de | natural | | | | | |
| 8 | roleplay | de | beginner | | | | | |
| 9 | roleplay | de | intermediate | | | | | |
| 10 | roleplay | de | natural | | | | | |
| 11 | podcast | es | natural | | | | | |
| 12 | podcast | es | natural | | | | | |
| 13 | podcast | es | beginner | | | | | |
| 14 | podcast | es | natural | | | | | |
| 15 | podcast | es | natural | | | | | |
| 16 | podcast | de | natural | | | | | |
| 17 | podcast | de | elementary | | | | | |
| 18 | podcast | de | natural | | | | | |
| 19 | podcast | de | natural | | | | | |
| 20 | podcast | de | natural | | | | | |

**Totals**: invented statements __ / 20 · every main point covered __ / 20 · same points __ / 20 ·
level limits met __ / __ (roleplay baseline __ / __)
