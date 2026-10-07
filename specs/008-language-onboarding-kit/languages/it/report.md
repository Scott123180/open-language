# Onboarding report: Italian (it)

Written by `kit.sh report it` from run-log.jsonl; regenerated in full, never edited by hand.

- Runs: 2026-10-07T22:43:27.648636+00:00 to 2026-10-07T23:01:17.440334+00:00
- Kit commands run: prereq, scaffold, apply, verify, check, bench

## Applied

- Data files: backend/app/language_data/languages/it.toml, backend/tests/integration/practice_languages/evaluation/it.toml
- Voices downloaded: it_IT-paola-medium, it_IT-riccardo-x_low

## Checks

- pytest: passed (2846 passed, 0 failed)
- ruff: passed
- black: passed
- mypy: passed
- eslint: skipped (--backend-only)
- vitest: skipped (--backend-only)
- playwright: skipped (--backend-only)
- Completeness check: passed

## Benchmarks

- adherence (llama3.1:8b): 46/50 against ≥ 95%: missed
- transcription, it_IT-paola-medium (base): 6/20 against ≥ 18/20: missed
- transcription, it_IT-riccardo-x_low (base): 5/20 against ≥ 18/20: missed

## Open items

- adherence missed: 46/50 against ≥ 95%
- transcription, it_IT-paola-medium missed: 6/20 against ≥ 18/20
- transcription, it_IT-riccardo-x_low missed: 5/20 against ≥ 18/20
- 4 review-sheet rows still to judge: specs/008-language-onboarding-kit/languages/it/review-sheet.md

## Not checked

- Listening to the voices
- Voice genders: asserted from the voice's name or model card, not checked by listening
- A screen-reader pass
- Offline use
- A human speaking into the microphone
