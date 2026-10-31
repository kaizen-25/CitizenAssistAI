# CitizenAssist AI — Technical Spec (v2)

## 0. Positioning
Most teams on statement #11 will build "RAG chatbot over scheme PDFs". We build something different: a deterministic eligibility engine with an AI interface on top.

| # | Differentiator | Why it matters to judges |
|---|---|---|
| 1 | Three-state eligibility (PASS / FAIL / UNKNOWN per rule), each rule cited to official text | Explainable; no hallucinated verdicts |
| 2 | Adaptive questioning: asks only the question that resolves the most schemes | Typically 3–6 questions instead of a long form (we measure this) |
| 3 | Document Unlock Plan: which document to get first, and the order after that | Directly answers "prepare document checklists" in the statement |
| 4 | Grounded Q&A that cites sources and refuses when the evidence is missing | Answers "find official links / eligibility" without fabrication |
| 5 | Printable helper packet for a volunteer or CSC operator | Reaches users who won't use an app themselves |

Scope: about 20–25 verified schemes. Mix central schemes (which apply in Punjab) and Punjab state schemes. Use two categories with heavy document overlap: Education/Scholarships and Social Welfare.

---

## 1. Repository layout
```
citizenassist/
  CLAUDE.md  SPEC.md  README.md  .env.example  .gitignore
  backend/
    app/
      main.py
      schemas.py          # all Pydantic models (single source of truth for API types)
      sessions.py         # in-memory session store (dict + TTL)
      api/                # route handlers only; no business logic
      engine/             # rules.py, eligibility.py, questions.py, explain.py
      unlock/             # graph.py
      llm/                # provider.py, extract_profile.py, chat.py, cache.py
      retrieval/          # bm25.py  (embed.py = P2)
      i18n/               # en.json hi.json pa.json  (operator templates, refusals, status labels)
      data/
        schemes.json
        documents.json
        profile_fields.json
        chunks.jsonl      # built by scripts/build_chunks.py
    tests/
      fixtures/           # synthetic schemes for engine tests (never real data)
    requirements.txt
  frontend/
    src/{pages,components,api,i18n,fixtures,types,hooks}
  sources/                # official PDFs/HTML saved by humans
    manifest.json         # [{file, url, title, retrieved_on}]
  evaluation/
    profiles.json         # hand-labelled test citizens
    qa_set.json           # chat test questions
    results/              # report.md + metrics.json (generated)
  scripts/
    validate_data.py  structure_scheme.py  build_chunks.py  run_evaluation.py
```

---

## 2. Stack (closed list)
| Layer | Choice | Notes |
|---|---|---|
| Frontend | React + Vite + TypeScript, Tailwind, lucide-react, react-router-dom, openapi-typescript | No UI kit needed |
| Fonts | Noto Sans, Noto Sans Devanagari, Noto Sans Gurmukhi (Google Fonts) | Required so Hindi and Punjabi render correctly |
| Backend | Python 3.11, FastAPI, Pydantic v2, uvicorn, pytest | |
| LLM | Gemini (`google-genai`, model taken from `GEMINI_MODEL` env) → Ollama (`OLLAMA_MODEL`, default `qwen3:4b`) → none | One interface; automatic fallback |
| Retrieval | `rank_bm25` over chunks; LLM translates non-English queries to English first | P1 |
| Retrieval (P2) | Multilingual embeddings (BGE-M3 or multilingual-e5-small, pre-downloaded), numpy in memory, reciprocal-rank fusion with BM25 | No vector DB at this scale |
| PDF text | `pypdf` | |
| Voice (P2) | Browser Web Speech API (recognition `hi-IN` / `pa-IN`, SpeechSynthesis) | Chrome only, needs network, optional |

No SQLite and no ChromaDB. At under 1,000 chunks they only add setup risk.

---

## 3. Data files

### 3.1 `profile_fields.json` — the field registry
This is the only set of profile fields that rules may reference. `validate_data.py` fails if a rule uses an unregistered field.
```json
{
  "field_id": "annual_family_income",
  "type": "number",
  "options": null,
  "unit": "INR_per_year",
  "min": 0, "max": 100000000,
  "sensitive": false,
  "allow_prefer_not_to_say": true,
  "ask_priority": 3,
  "label":    {"en": "Annual family income", "hi": "…", "pa": "…"},
  "question": {"en": "What is your family's total yearly income, approximately?", "hi": "…", "pa": "…"}
}
```
- `type` is one of `number | integer | enum | boolean`.
- Candidate fields (add only those that verified rules actually use): `state`, `age`, `gender`, `annual_family_income`, `social_category`, `education_level`, `currently_enrolled`, `course_level`, `occupation`, `has_disability`, `residence_area`, `holds_bpl_card`, `marital_status`.
- Mark `gender`, `social_category` and `has_disability` as `sensitive: true`. They are asked only when a rule needs them, and always offer "prefer not to say".
- An answer of "prefer not to say" stores the value `"__declined__"`, which evaluates as UNKNOWN.

### 3.2 `documents.json` — canonical document taxonomy
```json
{
  "income_certificate": {
    "label": {"en": "Income Certificate", "hi": "आय प्रमाण पत्र", "pa": "ਆਮਦਨ ਸਰਟੀਫਿਕੇਟ"},
    "aliases": ["income proof", "family income certificate"],
    "group": "financial",
    "issued_by_hint": "Sewa Kendra / Tehsil"
  }
}
```
- Starting set: `aadhaar_card`, `income_certificate`, `residence_certificate`, `caste_certificate`, `bank_passbook`, `birth_certificate`, `marksheet_previous`, `disability_certificate`, `ration_card`, `self_declaration`, `passport_photo`, `fee_receipt`.
- Aliases map free text to an ID. Merging two documents into one ID needs a human decision; never auto-merge.
- `issued_by_hint` is shown only if a human filled it in. Never generate it.

### 3.3 `schemes.json`
```json
{
  "scheme_id": "edu_001",
  "name": {"en": "Official scheme name exactly as on source"},
  "level": "central",
  "state": null,
  "category": "education",
  "department": "…",
  "summary": "1–2 sentences, from source",
  "benefits": "from source",
  "rules": [
    {
      "rule_id": "edu_001_r1",
      "field": "annual_family_income",
      "operator": "lte",
      "value": 250000,
      "applies_if": null,
      "kind": "hard",
      "source_excerpt": "≤ 30 words copied from the official guideline that justifies this rule"
    },
    {
      "rule_id": "edu_001_r2",
      "field": "course_level",
      "operator": "in",
      "value": ["post_matric", "undergraduate", "postgraduate"],
      "applies_if": {"field": "currently_enrolled", "operator": "eq", "value": true},
      "kind": "hard",
      "source_excerpt": "…"
    }
  ],
  "documents": [
    {"document_id": "income_certificate", "requirement": "mandatory", "applies_if": null},
    {"document_id": "caste_certificate",  "requirement": "mandatory",
     "applies_if": {"field": "social_category", "operator": "in", "value": ["SC", "ST", "OBC"]}}
  ],
  "unmapped_conditions": ["Criteria text that could not be encoded as a rule"],
  "application_url": "https://… (copied from official source only)",
  "application_mode": ["online"],
  "source": {"url": "…", "title": "…", "published": null, "retrieved_on": "2026-11-01", "file": "sources/edu_001.pdf"},
  "verification": {"status": "verified", "verified_by": "initials", "verified_on": "2026-11-01"}
}
```
- Operators: `eq neq gt gte lt lte in not_in`.
- Rule `kind`:
  - `hard`: evaluated by the engine.
  - `manual_check`: a real criterion that can't be checked from the profile (e.g. "attendance ≥ 75%"). It is never evaluated and is listed as "verify at application".
- `unmapped_conditions` are shown on the scheme page under "Other conditions — check the official source". Never drop them silently.
- The backend loads only `verification.status == "verified"` records unless `SHOW_UNVERIFIED=true` is set (dev only, with a visible banner).

### 3.4 `validate_data.py` must check
- Every rule field exists in `profile_fields.json`.
- Every operator is valid and the value type matches the field type.
- Every `document_id` exists in `documents.json`.
- Every scheme has a `source.url`, an `application_url` and a non-empty `source_excerpt` on each hard rule.
- IDs are unique.
- `verified_by` is set when the status is `verified`.
- Output: a pass/fail table, plus a count of verified records per category.

---

## 4. Eligibility engine (`engine/`), deterministic and pure

```python
evaluate_condition(cond, profile) -> bool | None      # None = needed field unknown/declined
evaluate_rule(rule, profile) -> RuleResult
evaluate_scheme(scheme, profile, held_docs) -> SchemeResult
evaluate_all(schemes, profile, held_docs) -> list[SchemeResult]
explain_rule(rule_result, lang) -> str               # template-based, no LLM
```

### 4.1 Rule outcomes
| Situation | Outcome |
|---|---|
| `kind == manual_check` | `MANUAL` |
| `applies_if` evaluates to None | `UNKNOWN` (the unknown field is the condition's field) |
| `applies_if` evaluates to False | `NOT_APPLICABLE` |
| Rule field is missing or `__declined__` | `UNKNOWN` |
| Comparison is true / false | `PASS` / `FAIL` |

### 4.2 Scheme status (hard rules only)
1. Any `FAIL` → `not_eligible`
2. Otherwise, any `UNKNOWN` → `cannot_determine`
3. Otherwise → `potentially_eligible`. Any `MANUAL` rules are listed as "verify at application".

### 4.3 Documents, which are separate from eligibility
For each document entry:
- `applies_if` = False → skip.
- `applies_if` = None → mark `possibly_required`.
- Otherwise, classify it by the user's answer as `held`, `missing` or `unsure`. Treat `unsure` as missing, with a flag.

`document_ready = (status == potentially_eligible) and no mandatory applicable doc is missing or unsure`

### 4.4 `SchemeResult`
```json
{
  "scheme_id": "edu_001",
  "status": "potentially_eligible | cannot_determine | not_eligible",
  "rules": [{"rule_id": "…", "outcome": "PASS", "explanation": "…", "source_excerpt": "…"}],
  "unknown_fields": ["social_category"],
  "manual_checks": ["…"],
  "documents": {"held": [], "missing": [], "unsure": [], "possibly_required": [], "optional_missing": []},
  "document_ready": false,
  "unmapped_conditions": [],
  "source": {"url": "…", "title": "…", "retrieved_on": "…"},
  "application_url": "…"
}
```
No percentage confidence scores.

### 4.5 Explanations
An explanation is built from the field label, an operator template and a formatted value. The field label comes from the registry and the operator template comes from `i18n/*.json`, e.g. `"lte": "{label} must be at most {value}"`.
- Values are formatted in Indian style: ₹2,50,000.
- This gives English, Hindi and Punjabi explanations with zero LLM calls, and numbers can never be altered by translation.

---

## 5. Adaptive questions (`engine/questions.py`)

```python
select_next_question(profile, schemes, asked: set[str], lang) -> Question | None
```

Algorithm:
1. Evaluate all schemes. Take the set S of schemes whose status is not `not_eligible`.
2. For each unanswered, unasked field f:
   `score(f)` = the number of schemes in S where f appears in an UNKNOWN hard rule, either as the rule field or as the `applies_if` field.
3. Pick the highest score. Break ties by lower `ask_priority`, then by `field_id`.
4. Return None when the best score is 0, or after 8 questions.
5. `state` is always asked first if it is unknown.

`Question`:
```json
{"field_id": "", "question_text": "", "answer_type": "", "options": [], "schemes_affected": 7, "reason": "Needed to check 7 schemes"}
```

Documents step: after eligibility questions finish, ask once with a checklist. List every document applicable to schemes in S; each answer is Have / Don't have / Not sure.

---

## 6. Document Unlock Plan (`unlock/graph.py`), the signature feature

```python
calculate_unlocks(results: list[SchemeResult]) -> UnlockReport
```

- **Candidates** are the schemes with `potentially_eligible` and `document_ready == false`. They are the only schemes that count.
- `cannot_determine` schemes go into `pending_info` and are never counted in the unlock numbers.

```json
{
  "ready_now": ["scheme_id"],
  "ranking": [
    {"document_id": "income_certificate", "label": "…", "rank": 1,
     "required_by": ["a","b","c","e"], "sole_blocker_for": ["a","c","e"]}
  ],
  "plan": [
    {"step": 1, "document_id": "income_certificate", "newly_ready": ["a","c","e"], "cumulative_ready": 3},
    {"step": 2, "document_id": "caste_certificate",  "newly_ready": ["b","d"], "cumulative_ready": 5}
  ],
  "pending_info": [{"scheme_id": "…", "unknown_fields": [], "missing_documents": []}]
}
```

- **Ranking:** sort by `len(required_by)` desc, then `len(sole_blocker_for)` desc. Documents that tie on both share the same rank.
- **Plan** (greedy): at each step, pick the document that makes the most candidates newly document-ready.
  - Tie → larger `required_by`, then `document_id`.
  - If no single document completes any scheme, pick the largest `required_by` as a progress step.
  - Stop when every candidate is ready.
- **Graph data:** documents on the left, candidate schemes on the right, an edge for each missing mandatory doc.
- **UI wording (fixed):** "Getting your {doc} could make you document-ready for {n} schemes that match what you've told us." Never use "guarantees" or "you will receive".

---

## 7. LLM layer (`llm/`)

### 7.1 Provider
`complete_json(system, user, json_schema, timeout=15) -> dict | None`
- Tries Gemini, then Ollama (`format: json`), then returns None.
- Every response is cached on disk by a hash of (provider, prompt).
- `DEMO_MODE=true` serves only from the cache, so the scripted demo survives a dead venue network.

### 7.2 Profile extraction (`POST /message`)
1. A deterministic parser runs first. It handles income such as `2 lakh`, `2.5 lac`, `₹2,00,000`, `दो लाख`, `ਦੋ ਲੱਖ`, `20k/month`. Monthly income is ×12, and the UI says so.
2. The LLM extracts the remaining fields.
   - Output per field: `{value, evidence: "<exact words from the user>", explicit: bool}`.
   - Allowed fields: registry fields only.
3. Validation:
   - Check type and range.
   - Enum values must match the options.
   - Drop sensitive fields where `explicit == false`.
4. Ranges or ambiguity (e.g. "2–3 lakh", "around 18 or 19") → return a clarification question. Never pick a value.
5. All extracted fields are marked `source: "extracted"`. The confirm screen must show them before any results.

### 7.3 Grounded Q&A (`POST /chat`)
1. If the language is not English and an LLM is available, translate the query to English.
2. Retrieve the BM25 top 6 chunks. If the top score is below the threshold, refuse.
3. The LLM answers using only the chunks and cites `[chunk_id]` after each claim.
4. Post-validation, done in code:
   - Every cited ID must be in the retrieved set.
   - Every number in the answer must appear in a cited chunk.
   - The answer must contain no URLs except ones that exist in `schemes.json`.
   - If any check fails, return the refusal plus the top 3 sources.
5. If no LLM is available, use extractive fallback: "Relevant official excerpts:" plus the top 3 chunks with their sources.
6. The refusal text, in all three languages, is "I cannot verify this from the available official sources."

### 7.4 Chunks (`build_chunks.py`)
- Sources: each verified scheme rendered as text, plus the official PDF/HTML text from `sources/`.
- Chunk at about 400 words with 50 words of overlap.
- Chunk format: `{chunk_id, scheme_id, source_url, source_title, text}`.

---

## 8. Multilingual
| Layer | How | Quality control |
|---|---|---|
| UI strings | `frontend/src/i18n/{en,hi,pa}.json` | Machine-translate once, then a native-speaking teammate reviews; each file has `"_reviewed": true/false` |
| Questions, field labels, doc labels | In the registry JSONs | Same review |
| Eligibility explanations | Templates (§4.5) | Numbers come from placeholders only |
| Scheme names | Official English name always shown | Optional translated subtitle labelled "machine-translated" |
| User free text in hi/pa | Handled directly by LLM extraction | Read-back confirmation |

Only claim the languages that `qa_set.json` and `profiles.json` actually tested.

---

## 9. API (all under `/api`)
| Method | Path | Body → Response |
|---|---|---|
| GET | `/health` | → `{llm_provider, llm_available, demo_mode, schemes_loaded, verified_by_category}` |
| POST | `/session` | `{language}` → `{session_id, first_question}` |
| POST | `/session/{id}/answer` | `{field_id, value}` → `{profile, next_question \| null, progress}` |
| POST | `/session/{id}/message` | `{text}` → `{extracted: [...], clarification \| null, profile, next_question}` |
| POST | `/session/{id}/documents` | `{document_id: "have" \| "missing" \| "unsure"}` → `{ok}` |
| POST | `/session/{id}/confirm` | `{profile_overrides?}` → `{confirmed: true}` |
| GET | `/session/{id}/results` | → `{confirmed, groups: {potentially_eligible, cannot_determine, not_eligible}}` |
| GET | `/session/{id}/unlock` | → `UnlockReport` |
| GET | `/session/{id}/packet` | → all data needed for the printable packet |
| GET | `/schemes`, `/schemes/{id}` | → verified records |
| POST | `/chat` | `{question, language, session_id?}` → `{answer, citations: [{chunk_id, source_url, source_title}], grounded: bool}` |

- Language comes from the session or an `Accept-Language` header.
- Sessions are kept in memory with a 2-hour TTL.
- API keys stay server-side only.

---

## 10. Frontend
**Pages**
- `/`: Landing
- `/assess`: chat panel with a "Use form instead" toggle, profile sidebar and progress
- `/confirm`: read-back of every field, with the extracted ones highlighted
- `/results`: three tabs/columns with counts
- `/documents`: unlock ranking, step plan and bipartite graph
- `/scheme/:id`: rule-by-rule table
- `/packet`: printable page

**Design**
- Light background, navy primary.
- Status colours: green = potentially eligible, amber = cannot determine, red = not eligible.
- Status is always icon + text label, never colour alone.
- Mobile-first layout.
- Tasteful civic dashboard; not a chat-app clone.

**Scheme card:** name, department, status chip, "matched X of Y criteria", unknown fields (with an "Answer now" button), missing docs, source + retrieved date, apply link.

**Scheme page:** each rule as a row showing outcome chip, explanation and `source_excerpt`, with a link to the official source. Below that, manual checks and unmapped conditions.

**Graph:** hand-rolled SVG in two columns. It's fine to skip the graph and ship only the ranked list plus plan if time is short.

**Packet:** `@media print` CSS and `window.print()`; no PDF library. It contains:
- confirmed profile (no identifiers)
- schemes by status
- document checklist
- unlock plan
- links
- sources with dates
- disclaimer
- a blank "Helper notes" box

**Disclaimer** (footer and packet): "CitizenAssist is an independent informational tool. It is not affiliated with any government body and cannot approve applications. Always confirm with the official source."

---

## 11. Evaluation (`scripts/run_evaluation.py`)

### 11.1 Inputs
**`profiles.json`:** 15–20 synthetic citizens.
- A teammate labels them by hand from the scheme rules **before** looking at engine output; otherwise the test is circular.
- Each profile has:
  - its full profile and held documents
  - `expected` status for each labelled scheme
  - `expected_top_document`
- Must include these cases:
  - all criteria pass
  - a single hard fail
  - a single unknown
  - a missing mandatory doc
  - a missing optional-only doc
  - two docs shared across schemes
  - no matches at all
  - a declined sensitive field
  - an ambiguous income input
  - a Hindi free-text intake
  - a Punjabi free-text intake

**`qa_set.json`:** 20 questions.
- 12 answerable (mixed en/hi/pa)
- 5 out of scope
- 3 asking about facts not in the sources

### 11.2 Metrics (all computed, none typed in)
- 3-class status accuracy plus a confusion matrix.
- Precision and recall for `potentially_eligible`.
- Top-1 unlock-document match rate.
- Adaptive vs static questioning:
  - An oracle answers the selector from the full profile.
  - Report the mean number of questions asked.
  - Compare against the static form size (registry fields used by any scheme).
  - Assert the final statuses equal the full-profile statuses, which proves no accuracy loss.
- Q&A: citation-validity rate, correct-refusal rate. Answer correctness is scored by a human into `qa_scores.json`; the script only aggregates it.
- Output: `evaluation/results/report.md` and `metrics.json`, including the date and the number of verified schemes.

---

## 12. Priorities and cut order
| Priority | Items |
|---|---|
| **P0** | Data files + validator, engine + tests, unlock plan + tests, API, results/scheme/documents pages, form intake, sources visible |
| **P1** | Adaptive questions, confirm screen, LLM extraction, grounded chat, Hindi, packet, evaluation report |
| **P2** | Punjabi, voice, embeddings, SVG graph, DEMO_MODE polish |

**Cut order:** voice → embeddings → graph → Punjabi → packet.

**Never cut:** the engine, sources or evaluation.

---

## 13. Acceptance
- [ ] `validate_data.py` passes with ≥ 15 verified schemes (target 25).
- [ ] `pytest` is green for the engine and unlock modules.
- [ ] The full flow works with `LLM_PROVIDER=none` and Wi-Fi off.
- [ ] Missing documents never change eligibility status.
- [ ] The unlock plan matches hand calculations on the test fixtures.
- [ ] Every rule shown in the UI has a source excerpt and a link.
- [ ] Every URL shown comes from `schemes.json`.
- [ ] `report.md` is generated from real runs.
- [ ] Languages claimed in the pitch equal the languages tested.
