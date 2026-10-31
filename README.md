# CitizenAssist AI

An English and Hindi navigator that tells a citizen which government schemes they may qualify for, why, what is still unknown, and which missing document to get first. Eligibility is decided by a deterministic engine, never by an LLM.

Read `CLAUDE.md` for the working rules, `SPEC.md` for the contract and `DESIGN.md` for the visual system.

## Setup
Needs Python 3.11 and Node 18 or later.

```bash
cp .env.example .env

cd backend
py -3.11 -m venv .venv              # macOS or Linux: python3.11 -m venv .venv
source .venv/Scripts/activate       # macOS or Linux: source .venv/bin/activate
                                    # PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd ..

cd frontend
npm install
```

## Run
With the venv active:

| What | Command |
| --- | --- |
| Backend dev server | `cd backend && uvicorn app.main:app --reload --port 8000` |
| Frontend dev server | `cd frontend && npm run dev` |
| Backend tests | `cd backend && pytest -q` |
| Regenerate API types | `cd frontend && npm run gen:types` (backend must be running) |
| Validate scheme data | `python scripts/validate_data.py` |

The API is at <http://localhost:8000/api/health> and the app at <http://localhost:5173>.

Set `VITE_USE_FIXTURES=true` in `.env` to run the frontend without the API.

## Configuration
| Variable | Meaning |
| --- | --- |
| `LLM_PROVIDER` | `gemini` (Gemini, then Ollama, then none), `ollama` or `none` |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | Gemini credentials and model |
| `OLLAMA_MODEL` | Ollama model, default `qwen3:4b` |
| `DEMO_MODE` | `true` serves LLM responses only from the disk cache |
| `SHOW_UNVERIFIED` | `true` loads unverified records and shows a banner. Dev only |
| `VITE_API_BASE_URL` | API origin for the frontend |
| `VITE_USE_FIXTURES` | `true` reads `frontend/src/fixtures/` instead of the API |
