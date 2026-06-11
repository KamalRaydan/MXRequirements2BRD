# Base Project Rules

## Philosophy
- Keep solutions simple and beginner-friendly.
- Prefer readable code over clever abstractions.
- Avoid unnecessary complexity.
- Never under any circumstances delete or add files outside of project directory unless explicitly told/approved.

## Workflow
- Explain the plan, with diagrams if necessary, before major changes.
- Do not refactor unrelated files.
- Prefer editing existing files over creating new ones.
- If you hit a decision point mid-build, stop and discuss it with me first.

## Dependencies
- Ask before installing packages.
- Prefer built-in tools first.
- Only install packages that are required as per the establish plan

## Coding
- Explain unfamiliar coding language syntax briefly.
- Avoid advanced abstractions unless necessary.

## Code Style
- Keep functions reasonably small.
- Add comments only when logic is not obvious.

## Testing
- Write unit tests for important business logic and critical new features.
- Prefer simple and readable tests.
- Prefer testing behavior over implementation details.
- Avoid excessive mocking unless necessary.

## Plans
- Always explain a plan in a language that a laymen can understand while keeping in the relevant technicalities wherever necessary.

---

# MaximoBRD Project Rules

**Authoritative spec:** `docs/implementation-spec.md` — use it for schemas, API contracts, prompts, and milestones. `docs/blueprint.md` is vision only.

## MVP-first scope (Milestones 0–1)
- Build the browser app at `http://127.0.0.1:8765` first. **No Electron** until Milestone 3.
- **Anthropic Claude only** (`claude-sonnet-4-6` default). No OpenAI, Ollama, or second providers until their milestone.
- Do not add deferred features (media processing, branded templates, cancel mid-run, Alembic, Windows packaging) unless explicitly working that milestone.
- Follow the repo layout in spec §6: `frontend/`, `backend/`, `knowledge/versions/`, `electron/` (empty until M3).

## Architecture
- **Backend:** FastAPI + **sync** SQLAlchemy + SQLite (`app.db` in OS app-data dir). Use `def` route handlers and `create_all()` at startup — no async DB driver, no Alembic yet.
- **Pipeline:** FastAPI `BackgroundTask` → sequential agents (extractor → summarizer → analyzer → generator) → `ProgressBus` → **SSE only** (no client polling).
- **Frontend:** React + Vite + Tailwind + Zustand. Vite dev proxy `/api` → backend. No `localStorage`/`sessionStorage`; no HTML `<form>` tags.
- **LLM:** All AI calls go through `backend/services/llm_client.py`. Only that file imports the `anthropic` SDK. JSON via tool-use + Pydantic validation; one "fix JSON" retry on schema failure.
- **Summarization:** When source `char_count > TOKEN_THRESHOLD` (12 000), run summarizer before analysis.

## Security & data
- API keys: macOS **Keychain** via Python `keyring` (MVP). Never in `.env`, DB, logs, or code. Electron `safeStorage` is Milestone 3.
- Bind backend to `127.0.0.1` only. Only send **extracted text** to LLM APIs — never raw audio, video, or binary.
- Maximo version facts live in `knowledge/versions/*.md`, injected at runtime — never hardcoded in Python or prompts.

## BRD output
- Structure from `backend/templates/brd_default_structure.json`. Requirement IDs: `BRD-{MODULE}-{NNN}` (deterministic post-LLM).
- DOCX via `python-docx`: named Word styles only, requirements as tables, DRAFT watermark via header XML injection.
- `POST /generate` requires ≥1 source with `processing_status = EXTRACTED`. Media files stay `PENDING` until Milestone 5.
