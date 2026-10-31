# CitizenAssist — Team plan + Claude Code phase prompts

Put `CLAUDE.md` and `SPEC.md` in the repo root before the first prompt.
Claude Code reads CLAUDE.md automatically; the prompts below assume SPEC.md is already there.
Give Claude Code one phase at a time. A single 24-hour mega-prompt produces unverified sprawl.

---

## A. Before the hackathon (check what the rules allow)
- [ ] **Ask the organisers** whether pre-collected public data and a pre-written spec are allowed. Code usually has to be written on site.
- [ ] If data prep is allowed, save official PDFs/pages for about 30 candidate schemes into `sources/` with `manifest.json`. This is the single biggest time-saver.
- [ ] Pre-install everything on every laptop; venue Wi-Fi will be bad:
  - Node + npm cache, Python 3.11, `pip download` the wheels.
  - `ollama pull qwen3:4b`
  - For the P2 embeddings path only: the embedding model weights.
- [ ] Test the Gemini key and check its current free-tier limits.
- [ ] Confirm which teammate can review Hindi and Punjabi strings.

---

## B. Team split (4 people, 4 parallel tracks)
| Person | Track | Owns |
|---|---|---|
| Backend dev | **Engine + API** | `engine/`, `unlock/`, `api/`, `sessions.py`, all pytest |
| AI coder 1 (Claude Code session 1) | **Frontend** | All pages, built against fixtures first |
| AI coder 2 (Claude Code session 2) | **Data tooling + LLM + i18n** | `structure_scheme.py`, `validate_data.py`, `build_chunks.py`, `llm/`, `retrieval/`, translations |
| Pitch lead | **Truth + story** | Verifies every scheme against its source, hand-labels `profiles.json` and `qa_set.json`, reviews translations, writes slides and the demo script, records the backup video |

The pitch lead is a co-owner of correctness, not idle until hour 20. Human verification is our moat.

Run the two Claude Code sessions in **separate git worktrees or branches**. SPEC.md is the contract, so they won't drift. Merge at each gate.

---

## C. Gates (human schedule; Claude Code doesn't track time)
| By hour | Gate | Pass condition |
|---|---|---|
| 1 | **G0 Scaffold** | Both servers run; `/api/health` returns OK; frontend shell renders; validator runs |
| 5 | **G1 Core** | ≥ 12 verified schemes; engine + unlock tests green; 5 synthetic profiles run end-to-end via CLI and match hand calculations |
| 11 | **G2 E2E (no LLM)** | Form intake → confirm → results → documents works in a browser with `LLM_PROVIDER=none` |
| 15 | **G3 AI + Hindi** | NL intake, grounded chat with refusal, Hindi UI; ≥ 18 verified schemes |
| 16 | **FEATURE FREEZE** | |
| 18 | **G4 Eval** | `report.md` generated |
| 20 | **G5 Demo-ready** | Packet prints; DEMO_MODE cached; backup video recorded |

If G1 is missed, cut data to 15 schemes and drop Punjabi immediately.

---

## D. Phase prompts (copy-paste into Claude Code)

### Phase 0 — Scaffold (session 1, plan mode)
```
Read CLAUDE.md and SPEC.md fully. Use plan mode first and show me the plan.

Then scaffold the monorepo exactly as SPEC §1:
- FastAPI app with GET /api/health and CORS for the Vite dev server.
- All Pydantic models from SPEC §3, §4.4, §5, §6 and §9 in backend/app/schemas.py.
- Empty-but-importable engine/, unlock/, llm/ and retrieval/ modules with the function signatures from the spec. Bodies raise NotImplementedError.
- scripts/validate_data.py, fully implemented per SPEC §3.4.
- Seed data/documents.json with the starting taxonomy. Seed profile_fields.json with the candidate fields: English text filled in, hi/pa set to "" for now.
- Frontend: Vite + React + TS + Tailwind + react-router. Routes for every page in SPEC §10 as placeholders. A tiny useT() i18n hook reading src/i18n/{en,hi,pa}.json. Noto fonts loaded. An `npm run gen:types` script using openapi-typescript against http://localhost:8000/openapi.json.
- README with setup commands; .env.example with LLM_PROVIDER, GEMINI_API_KEY, GEMINI_MODEL, OLLAMA_MODEL, DEMO_MODE, SHOW_UNVERIFIED.

Do NOT create any real scheme records. Do NOT implement features yet.
Finish with: files created, how to run, and any contradictions you found in SPEC.md.
```

### Phase 1 — Engine + unlock (backend dev's session)
```
Implement SPEC §4, §5 and §6 in backend/app/engine/ and backend/app/unlock/.

First write tests/fixtures/synthetic_schemes.json: 6 made-up schemes (ids syn_a..syn_f) with names clearly marked SYNTHETIC. They must cover:
- every operator
- an applies_if rule
- a manual_check rule
- a conditional document
- two documents shared across schemes

Then write the tests BEFORE the implementation. Cover:
- rule outcomes table (§4.1), every row
- scheme status precedence (§4.2)
- "missing document never changes status"
- "__declined__ evaluates UNKNOWN"
- select_next_question: picks the max-score field, never repeats, returns None at score 0
- unlocks: the 5-scheme example (income cert required_by 4, caste cert required_by 2)
- unlocks: cannot_determine schemes excluded from counts
- unlocks: ties share a rank
- unlocks: the greedy plan with a "no single doc completes a scheme" case
- Indian number formatting (₹2,50,000)

Implement until all tests are green. Add scripts/run_profile.py that prints results + unlock report for a profile JSON, for CLI checking.

Report the test results.
```

### Phase 2 — Data structuring tool (session 2)
```
Build scripts/structure_scheme.py:
- Input: a text/PDF file from sources/ plus its source URL.
- It calls llm.provider.complete_json to draft ONE scheme record in the SPEC §3.3 format.
- Hard constraints:
  - status is always "unverified"
  - every hard rule needs a source_excerpt copied verbatim from the input text
  - anything ambiguous goes to unmapped_conditions
  - application_url only if it appears literally in the input, else null
- Output: a draft into data/drafts/<id>.json, then run validate_data.py on it.

Also build a small `scripts/verify.py <id>` that pretty-prints the draft beside its source excerpts. A human uses it to tick each rule, then it moves the record into schemes.json with verification fields set.

Implement llm/provider.py now as well (SPEC §7.1), including the disk cache and DEMO_MODE.

Never generate scheme content from your own knowledge.
```

### Phase 3 — Frontend on fixtures (session 1)
```
Create frontend/src/fixtures/ with realistic JSON for every API response in SPEC §9, using the SYNTHETIC schemes. Build all pages in SPEC §10 against the fixtures, toggled by VITE_USE_FIXTURES.

Priority order:
1. results
2. scheme detail
3. documents (ranked list + step plan)
4. form intake + confirm
5. chat intake
6. landing
7. packet

Design per SPEC §10. Status must always be icon + label. Check 375px mobile width.

All user-facing strings go through useT().
```

### Phase 4 — Wire API (backend dev)
```
Implement every route in SPEC §9 using the engine, sessions.py (in-memory, 2h TTL) and the loaded verified data.
- /message and /chat may return 503 with a clear message until Phase 5.
- Add API tests with FastAPI TestClient for the full form flow.
- Then: npm run gen:types in the frontend and switch VITE_USE_FIXTURES=false. Fix type errors.

Gate G2: the full flow works in the browser with LLM_PROVIDER=none.
```

### Phase 5 — AI features (session 2)
```
Implement SPEC §7.2 (profile extraction with the deterministic income parser first, clarification on ambiguity) and §7.3/§7.4 (build_chunks.py, BM25, grounded chat with code-level post-validation and the extractive fallback).

Unit-test:
- the income parser (lakh / lac / ₹ / commas / k / monthly / Hindi / Punjabi words / ranges → clarification)
- the citation validator (fabricated ID rejected, unseen number rejected, unknown URL rejected)

Show me 5 real chat transcripts, including 2 refusals.
```

### Phase 6 — Languages (session 2)
```
Fill hi and pa in profile_fields.json, documents.json, i18n/*.json (backend + frontend):
- machine-translate
- keep placeholders intact
- set "_reviewed": false

Add a script that lists every string with missing or mismatched placeholders.

Do not translate scheme names or any number.
```
After this, the reviewer fixes the strings and flips `_reviewed` to true.

### Phase 7 — Evaluation (either session, after freeze)
```
Implement scripts/run_evaluation.py per SPEC §11 using evaluation/profiles.json and qa_set.json, which humans wrote.
- Do not modify the expected labels. If a label looks wrong, list it for a human to review instead.
- Generate report.md + metrics.json.
```

### Phase 8 — Packet + demo hardening
```
- Finish /packet with print CSS.
- Run the demo script in section E below with DEMO_MODE=false to warm the cache, then verify it replays with DEMO_MODE=true and Wi-Fi off.
- Fix only bugs; no new features.
```

---

## E. 3-minute demo
| Time | Beat |
|---|---|
| 0:00–0:25 | **Problem.** A real-sounding synthetic citizen, e.g. a 19-year-old in Ludhiana whose mother is a daily-wage worker. There are schemes she qualifies for, but the documents and portals are a maze. |
| 0:25–1:00 | **Intake in Hindi** (typed; voice is a bonus). The system asks only about 3–4 questions and says *why* it asks each one. Show the read-back confirm screen. |
| 1:00–1:35 | **Results.** Show the three groups. Open one scheme: each rule is green, red or amber with an official excerpt + link. Open one "cannot determine": answer the missing question live, and it moves. |
| 1:35–2:15 | **Unlock plan.** "Get your income certificate first; it makes you document-ready for 3 schemes. Then the caste certificate: +2." This is the moment to land. |
| 2:15–2:35 | **Grounded chat.** One answered question with citations, then one trick question → refusal. |
| 2:35–2:45 | **Packet.** Print preview for the Sewa Kendra helper. |
| 2:45–3:00 | **Evidence.** Real numbers from report.md: verified schemes, status accuracy, average questions vs form size, refusal rate, languages tested. Then one limitations line. |

**Answers for judges' likely questions:**
- *Why not just a chatbot?* Because an LLM can't be trusted to decide eligibility. Ours is auditable, rule by rule.
- *How do you keep data fresh?* Every record carries a source, a retrieved date and a verifier. The structure tool cuts adding a scheme to minutes.
- *Scale?* The schema is state-agnostic; more states means more verified records, not new code.
