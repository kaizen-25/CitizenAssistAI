# CitizenAssist AI — rules for Claude Code

Read `SPEC.md` before doing anything, including the decisions in §14, which override earlier sections. SPEC.md is the contract between the frontend, backend and data.
If you think the spec is wrong or contradictory, say so and stop. Do not silently deviate.

## What this is
A 24-hour hackathon MVP (GRAVITON 2026, problem statement #11).
It is an English and Hindi navigator that tells a citizen:
- which government schemes they *may* qualify for,
- why, with an official source for every rule,
- what is still unknown,
- which missing document to get first.

It is not a chatbot, and it never approves an application.

## Non-negotiables
1. Eligibility is decided only by the deterministic engine in `backend/app/engine/`.
   - An LLM never decides eligibility.
   - An LLM never produces a URL, a threshold, a fee or a deadline.
2. Never invent scheme data.
   - Scheme facts come only from `backend/app/data/schemes.json`. Claude fetches the official sources and verifies each record against them, with `verified_by: "claude"`. Never describe this data as human-verified.
   - If asked to create scheme records, structure ONLY the official text you were given.
   - Set `verification.status = "unverified"`.
   - Put anything you could not encode into `unmapped_conditions`.
3. Unknown is never a pass. A missing document is never an eligibility failure.
4. The full flow must work with `LLM_PROVIDER=none` and no internet. The flow is: form intake → confirm → results → unlock plan → packet.
5. Never fabricate evaluation numbers. Metrics come only from `scripts/run_evaluation.py` output.
6. Collect no Aadhaar numbers, bank details, names, phone numbers or addresses. Sessions live in memory only.
7. Numbers inside any translated or generated string are inserted through placeholders. Translation never touches them.

## How to work
- Work in small increments. After any change in `engine/` or `unlock/`, run `pytest -q` in `backend/`. Do not move on while tests fail.
- Keep the app runnable at all times. Commit at every gate with the message `gate: <name>`.
- Until the API is live, the frontend reads fixtures from `frontend/src/fixtures/`. The fixtures match the SPEC API shapes. Toggle with `VITE_USE_FIXTURES=true`.
- After any API model change, regenerate frontend types from FastAPI's OpenAPI schema with `npm run gen:types`. Never hand-edit the generated types.
- Do not add dependencies beyond those listed in SPEC §2 without asking first.
- Do not add Docker, auth, a database server or microservices.
- Frontend work follows `DESIGN.md`, which adapts the Hallmark skill in `.claude/skills/hallmark/` to SPEC §10. SPEC wins any conflict.
- When blocked, say so plainly. Never hide a gap behind mock data outside `fixtures/`.
- End every task with:
  - files changed
  - tests run and their results
  - open issues
  - whether the current gate is met

## Commands
| What | Command |
|---|---|
| Backend dev server | `cd backend && uvicorn app.main:app --reload --port 8000` |
| Backend tests | `cd backend && pytest -q` |
| Frontend dev server | `cd frontend && npm run dev` |
| Regenerate API types | `cd frontend && npm run gen:types` |
| Validate scheme data | `python scripts/validate_data.py` |
| Build RAG chunks | `python scripts/build_chunks.py` |
| Run evaluation | `python scripts/run_evaluation.py` |
