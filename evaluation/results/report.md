# CitizenAssist evaluation report

Date: 2026-10-31. Verified schemes: 12 {'education': 6, 'social_welfare': 6}. LLM provider setting: ollama.

## Limits of this evaluation
- Scheme records were structured and verified by Claude, not by a human.
- Evaluation labels were written by Claude from the scheme rules, so they are not independent.
- Hindi is machine-translated and unreviewed. Punjabi was cut and is not claimed.
- Answer correctness was not scored, because `qa_scores.json` needs a human reviewer.

## Eligibility status
- Labels: 91
- 3-class accuracy: 100.0%
- Precision for potentially eligible: 100.0%
- Recall for potentially eligible: 100.0%

| Expected \ Actual | potentially_eligible | cannot_determine | not_eligible |
| --- | --- | --- | --- |
| potentially_eligible | 34 | 0 | 0 |
| cannot_determine | 0 | 10 | 0 |
| not_eligible | 0 | 0 | 47 |

Mismatches: 0

## Document unlock
- Profiles checked: 6
- Top-1 document match: 100.0%

## Adaptive questioning
- Mean questions asked: 7.06 (most: 8)
- Static form size: 10 fields
- Profiles whose final status differed from the full profile: 3 of 18
- Individual scheme status differences: 6

## Free-text intake
- Pass rate: 100.0% across 2 runs

## Grounded Q&A
- Questions: 20 (en, hi)
- Answerable questions answered: 66.7%
- Correct refusal rate: 100.0%
- Citation validity: 100.0%

## Coverage gaps
- No profile covers the required case: a missing optional-only doc
