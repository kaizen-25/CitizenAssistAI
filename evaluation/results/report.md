# CitizenAssist evaluation report

Date: 2026-10-31. Verified schemes: 18 {'education': 8, 'social_welfare': 10}. LLM provider setting: ollama.

## Limits of this evaluation
- Scheme records were structured and verified by Claude, not by a human.
- Evaluation labels were written by Claude from the scheme rules, so they are not independent.
- Hindi is machine-translated and unreviewed. Punjabi was cut and is not claimed.
- Answer correctness was not scored, because `qa_scores.json` needs a human reviewer.

## Eligibility status
- Labels: 117
- 3-class accuracy: 100.0%
- Precision for potentially eligible: 100.0%
- Recall for potentially eligible: 100.0%

| Expected \ Actual | potentially_eligible | cannot_determine | not_eligible |
| --- | --- | --- | --- |
| potentially_eligible | 44 | 0 | 0 |
| cannot_determine | 0 | 11 | 0 |
| not_eligible | 0 | 0 | 62 |

Mismatches: 0

## Document unlock
- Profiles checked: 8
- Top-1 document match: 100.0%

## Adaptive questioning
- Mean questions asked: 7.61 (most: 8)
- Static form size: 11 fields
- Profiles whose final status differed from the full profile: 8 of 28
- Individual scheme status differences: 16

## Free-text intake
- Pass rate: 88.9% across 9 runs

## Grounded Q&A
- Questions: 38 (en, hi)
- Answerable questions answered: 100.0%
- Hindi answerable questions answered: 100.0%
- Excerpt fallbacks, not counted as answers: 0
- Correct refusal rate: 91.7%
- Citation validity: 100.0%

## Coverage gaps
