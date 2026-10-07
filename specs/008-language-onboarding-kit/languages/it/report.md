# Onboarding report: Italian (it)

Written by `kit.sh report it` from run-log.jsonl; regenerated in full, never edited by hand.

- Runs: 2026-10-07T22:43:27.648636+00:00 to 2026-10-07T22:54:26.908109+00:00
- Kit commands run: prereq, scaffold, apply, verify, check

## Applied

- Data files: backend/app/language_data/languages/it.toml, backend/tests/integration/practice_languages/evaluation/it.toml
- Voices downloaded: it_IT-paola-medium, it_IT-riccardo-x_low

## Checks

- pytest: passed (2845 passed, 0 failed)
- ruff: passed
- black: passed
- mypy: passed
- eslint: passed
- vitest: passed (754 passed, 0 failed)
- playwright: passed (285 passed, 0 failed)
- Completeness check: passed

## Benchmarks

- Not run yet: kit.sh bench it

## Open items

- None.

## Not checked

- Listening to the voices
- Voice genders: asserted from the voice's name or model card, not checked by listening
- A screen-reader pass
- Offline use
- A human speaking into the microphone
