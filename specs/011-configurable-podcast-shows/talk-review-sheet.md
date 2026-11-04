# Talk review sheet: Configurable Podcast Shows (011)

Hand-run on the default local setup: Ollama `llama3.1:8b` on an RTX 3070 Ti (8 GB), Piper voices,
Spanish, 2026-11-04. T063 is **not complete**: only the latency benchmark ran in full; the
host-talk benchmark had a one-episode-per-format sanity run, not the 20 + 20 the review needs.

## SC-011: time to the first sentence's audio (T062 latency benchmark, 20 Continues per length)

| Host lines | p90 to first part's audio | Target | Result |
|---|---|---|---|
| Short | 4.45 s | ≤ 5 s | met |
| Medium | 5.19 s | ≤ 5 s | **missed** |
| Long | 5.65 s | ≤ 5 s | **missed** |

T063's rule: "If SC-011 misses (p90 > 5 s for any length), stop and report before US2."

## R18: context size

`prompt_eval_count` at the end of a Long episode of Long lines: **4094**. That is Ollama's default
context of 4096 tokens, so the prompt is very likely being truncated. Record in
`docs/architecture.md` § "Open items" with the configurable `num_ctx` option (T131).

## Host talk, sanity run only (1 Medium One host + 1 Medium Panel episode, Beginner, defaults)

| Criterion | Measured | Target |
|---|---|---|
| SC-001 median sentences per discussion line | 3.0 | ≥ 3 |
| SC-001 inviting share before the wrap-up | 0.53 | ≤ 0.50 (missed) |
| SC-013 median sentences per explain/answer line | 4.0 | ≥ 4 |
| SC-002 sentences within 8 words | 0.07 | ≥ 0.90 (missed badly) |
| SC-015 episodes signed off after the last thought | 2 / 2 | 100% |
| SC-005 longest run without an invitation | ≤ 4 | ≤ 4 |
| R19 address tag share | 42 / 42 | (recorded) |

Observations from the transcripts: answers to the learner's questions came in the very next line
(SC-003 looks good), openings named one subject and wrap-ups said the show was nearly over
(SC-014 looks good), but Beginner sentences were long and complex, often 15–25 words, with past
and conditional tenses. `llama3.1:8b` does not keep three-to-five-sentence lines at Beginner level.

## Still to run

- The full host-talk benchmark (20 + 20 episodes), plus 10 Presented and 10 Conversation for SC-004.
- The guest-episode benchmark (T128) once US4 exists.
- SC-003, SC-012, SC-014 and SC-016 transcript reviews.
