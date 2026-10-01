# Speaker Review Sheet (SC-004)

**Feature**: [spec.md](spec.md) | **Benchmark**: `backend/tests/integration/podcasts/test_speaker_review_benchmark.py`

Run the benchmark on the default local setup (`llama3.1:8b`, both Spanish voices installed):

    backend/.venv/bin/pytest -m benchmark -s tests/integration/podcasts -k speaker_review

It prints 10 medium-length episodes (5 Listen, 5 Panel). For each one it lists the hosts and their
personalities, then every host line numbered **with its speaker's name removed**, then an answer
key. For each line, read it (and play it: `GET /api/audio/tts/{message id}` in a running app on the
same database) and write down which host you think said it, **before** reading the key. Then fill in
the true speaker from the key.

**Bar** (spec SC-004): the reviewer names the right host for **at least 80%** of lines across the
10 episodes.

**Status**: not yet run. The session that built 007 had no Ollama or Piper voices, so the rows below
are empty. Record the result in `docs/architecture.md` § "Open items" if the bar is missed.

Add one row per host line; a medium episode has about 20. The first rows of episode 1 show the shape.

| Episode | Format | Line | Reviewer's guess | True speaker | Correct? |
|---|---|---|---|---|---|
| 1 | listen | 1 | | | |
| 1 | listen | 2 | | | |
| 1 | listen | 3 | | | |
| … | | | | | |
| 6 | panel | 1 | | | |
| … | | | | | |

**Per episode**:

| Episode | Format | Hosts (personalities) | Lines | Correct | % |
|---|---|---|---|---|---|
| 1 | listen | | | | |
| 2 | listen | | | | |
| 3 | listen | | | | |
| 4 | listen | | | | |
| 5 | listen | | | | |
| 6 | panel | | | | |
| 7 | panel | | | | |
| 8 | panel | | | | |
| 9 | panel | | | | |
| 10 | panel | | | | |

**Total**: __ correct of __ lines = __% (bar: ≥ 80%)
