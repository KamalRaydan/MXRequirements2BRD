# MaximoBRD — Implementation Specification (MVP-First)

This document is everything needed to implement the project without referring back to `docs/blueprint.md`. It resolves ambiguities, defines schemas and API contracts, specifies prompts, and lays out a milestone plan that produces a **working application within the first two weeks** and grows it — without rework — into the full desktop product.

**Status:** Milestone 5 in progress (`feat/milestone-5-media-mas8`) — media processing (audio/video/image) + MAS 8 knowledge. Milestones 0–4 complete: desktop app (Electron shell + macOS DMG) wrapping the same backend + frontend, with Anthropic + OpenAI providers
**Platform:** macOS shipping (DMG); backend is cross-platform so Windows packaging is a build-on-Windows follow-up
**MVP shape:** Local web app — Python FastAPI backend + React frontend in the browser at `localhost`
**Target shape:** Same backend + same frontend wrapped in an Electron desktop shell (Milestone 3 ✅)

---

## 1. Product Goal

A local-first desktop app for IBM Maximo consultants that:

1. Creates a project (client, name, date, Maximo version, folder location).
2. Accepts requirement artifacts (documents now; audio/video/images later).
3. Runs a 3-stage pipeline (extract → analyze → generate/render).
4. Exports a DRAFT-watermarked DOCX BRD with traceable requirement IDs.

---

## 2. Build Strategy — Walking Skeleton

The previous revision of this spec front-loaded Electron, dual AI providers, and packaging into one 6–8 week phase; the first end-to-end BRD would not have existed until week 5–6. This revision inverts that:

> **Build the thinnest complete slice first** (project → upload → pipeline → DOCX), running in the browser, then thicken it milestone by milestone until it matches the full blueprint.

```
 Milestone 0        Milestone 1            Milestone 2         Milestone 3        Milestone 4+
 (1–2 days)         (~2 weeks)             (1–2 weeks)         (1–2 weeks)        (per roadmap)
┌────────────┐   ┌─────────────────┐   ┌────────────────┐   ┌──────────────┐   ┌──────────────┐
│ Scaffold + │   │  WORKING MVP    │   │  Hardening +   │   │  Electron    │   │ OpenAI, media│
│ health     │ → │  upload → BRD   │ → │  branded tmpl, │ → │  shell, DMG, │ → │ MAS 8, brand │
│ check      │   │  in the browser │   │  cancel, tests │   │  safeStorage │   │ clone,Ollama,│
└────────────┘   └─────────────────┘   └────────────────┘   └──────────────┘   │ Windows      │
                                                                               └──────────────┘
```

**Why nothing is thrown away later:** the FastAPI backend, REST/SSE contracts, SQLite schema, agents, prompts, and the entire React UI are identical in browser and Electron modes. When Electron arrives (Milestone 3) it only adds a window around the same `localhost` app, swaps API-key storage from macOS Keychain to Electron `safeStorage`, and replaces browser file pickers with native dialogs.

---

## 3. Decisions

### 3.1 MVP decisions (Milestones 0–1)

| Topic | MVP decision |
|-------|--------------|
| Shell | Browser at `http://127.0.0.1:8765` — no Electron yet |
| AI provider | **Anthropic Claude** (`claude-sonnet-4-6` default) + **OpenAI** (`gpt-4o` default) — user-selectable (Milestone 4 pulled forward) |
| API key storage | macOS Keychain via Python `keyring`, **one entry per provider** — never in DB, logs, code, or `.env` |
| Database | **One SQLite file** `app.db` in OS app-data dir (projects + sources + runs + settings) |
| Migrations | None yet — `SQLAlchemy create_all()` at startup |
| Project files | Per-project folder, default `~/MaximoBRD/{client}-{project}` (path editable as text) |
| BRD structure | `brd_default_structure.json` only |
| Traceability | Document-level (`source_ref` = filename) |
| Progress | SSE only — no client polling |
| Agents | Sequential only — no parallel agent execution |
| Context overflow | Per-source summarization when `char_count > TOKEN_THRESHOLD` |
| Text files | PDF, DOCX, TXT, MD, XLSX, XLS — extracted on upload |
| Media files | Accepted and stored; status `PENDING`; skipped in pipeline |
| Maximo versions | 7.6.0.x, 7.6.1.x, MAS 9.x enabled; MAS 8.x disabled ("Coming soon") |
| Export | Browser file download of the DOCX |

### 3.2 Deferred decisions (still part of the target — moved, not dropped)

| Topic | Target decision | Lands in |
|-------|-----------------|----------|
| Electron shell + packaging | Built in Milestone 3 — **same-origin** design (window loads the backend's own URL) instead of an IPC bridge; see §13 | Milestone 3 ✅ |
| API keys in Electron `safeStorage` | **Declined** — kept `keyring`, which is already cross-platform (macOS Keychain, Windows Credential Locker, Linux Secret Service). safeStorage would have required the IPC/header-injection design the same-origin shell avoids | Not needed |
| Native file/folder/save dialogs | **Deferred** — Chromium's drag-drop, `<input type=file>`, and `<a download>` work inside the Electron window; native dialogs are polish | Milestone 8 |
| Portable per-project `project.db` | **Deferred** — kept the single shared `app.db` (all rows already keyed by `project_id`, so the split stays a non-breaking data move) | Later, if needed |
| Branded DOCX → heading-structure extraction | `StructureExtractor` | Milestone 2 ✅ |
| Audio/video/image processing (Whisper, ffmpeg, vision) | `PENDING → TRANSCRIBING → EXTRACTED` | Milestone 5 |
| MAS 8.x knowledge + enablement | `mas-8.md` | Milestone 5 |
| Visual branding clone (fonts/logo/tables) | `BrandingProfile` | Milestone 6 |
| Ollama local models | `OllamaProvider` | Milestone 7 |
| Windows build, signing, onboarding polish | electron-builder + PyInstaller | Milestone 8 |
| Alembic migrations | Introduce once schema churn matters (still no churn through M3 — `create_all()` remains sufficient) | Later, if needed |

---

## 4. MVP Scope (Milestone 1 exit)

**A consultant can:** create a project → upload PDF/DOCX/TXT/MD/XLSX files → click Generate → watch live progress → download a DRAFT-watermarked DOCX BRD with `BRD-{MODULE}-{NNN}` requirement tables citing source filenames.

**Explicitly in:** project CRUD, streaming upload, background text extraction with status badges, provider settings (Claude or OpenAI) + per-provider Keychain keys + test connection, 3-stage pipeline with SSE progress, summarization fallback for oversized sources, DOCX render + download, media files accepted as `PENDING` without breaking generation.

**Explicitly out (per §3.2):** Electron, branding, cancel mid-run (Milestone 2), run-history polish, media processing, packaging.

---

## 5. Architecture

### 5.1 MVP architecture (Milestones 0–2)

```
Browser (React + Vite + Tailwind + Zustand)
   │  fetch / EventSource
   ▼
FastAPI @ 127.0.0.1:8765
  ├── routes/       REST + SSE
  ├── services/     LLMClient (Anthropic + OpenAI), DocxRenderer, ProgressBus
  ├── agents/       extractor, summarizer, analyzer, generator (sequential)
  ├── processors/   per file-type text extraction
  ├── models/       Pydantic inter-stage contracts
  └── db/           SQLAlchemy (sync) + SQLite

macOS Keychain (via `keyring`)   ← API key lives here only

App data dir (~/Library/Application Support/MaximoBRD/)
  └── app.db

Project folder (default ~/MaximoBRD/{client}-{project}/)
  ├── sources/          raw uploads
  ├── extracted/        {source_id}.txt sidecars
  └── output/           {run_id}.docx
```

Implementation simplicity choices (beginner-friendly, low maintenance):

- **Sync SQLAlchemy** sessions in `def` endpoints (FastAPI runs them in a threadpool). No async DB driver, no Alembic yet.
- **Pipeline runs as a FastAPI `BackgroundTask`**; it publishes progress events to an in-memory **ProgressBus** (`dict[run_id] → list[event]`). The SSE endpoint streams new events from that list (server-side check every ~300 ms; the client never polls).
- **One process to debug** in MVP: `uvicorn`. Vite dev server proxies `/api` during development; `npm run build` output can be served by FastAPI for a single-command run.

### 5.2 Desktop architecture (Milestone 3 — as built)

The shell is deliberately thin. Because FastAPI already serves the built React app at
`/` and the API at `/api`, the Electron window just loads the backend's own URL — so the
renderer is **same-origin** with the backend and the existing frontend (`fetch`,
`EventSource`, multipart uploads) runs **unchanged**. No IPC bridge, no `api.js` rewrite.

```
Electron Main (electron/main.js)
  ├── picks a free port
  ├── spawns the backend on it (MAXIMOBRD_PORT)
  │      • packaged: the PyInstaller binary in resources/backend/
  │      • dev:      the backend venv's python run_server.py
  ├── health-gates: polls GET /health (every 500 ms, max 30 s)
  └── opens BrowserWindow → http://127.0.0.1:<port>/   (same-origin with the API)
        │
Electron Renderer = the same React app, served by FastAPI  (api.js untouched)
        │
FastAPI backend = unchanged (binds 127.0.0.1 only; reads the API key from keyring)
```

Process lifecycle: find free port → spawn backend → poll `GET /health` every 500 ms
(max 30 s) → show window; on quit SIGTERM the child, wait 5 s, then SIGKILL. Dev mode
reuses an externally running uvicorn via `BACKEND_DEV=1`. API keys stay in the OS
credential store via `keyring` (cross-platform) — no migration needed.

---

## 6. Repository Layout

Laid out from day one so Electron drops in without restructuring:

```
maximobrd/
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api.js                    (single API layer — fetch/EventSource; swaps to IPC in M3)
│   │   ├── components/
│   │   │   ├── StatusBadge.jsx
│   │   │   └── ErrorBoundary.jsx        (wraps all routes — structured error fallback)
│   │   ├── pages/
│   │   │   ├── ProjectList.jsx
│   │   │   ├── ProjectDetail.jsx
│   │   │   ├── Generate.jsx
│   │   │   └── Settings.jsx
│   │   └── store/
│   │       ├── projectStore.js
│   │       ├── settingsStore.js
│   │       └── pipelineStore.js
│   ├── dist/                         (built output served by FastAPI in single-command mode)
│   ├── package.json
│   └── vite.config.js                (dev proxy /api → 127.0.0.1:8765; uses @tailwindcss/vite)
├── backend/
│   ├── main.py
│   ├── run_server.py                  (standalone launcher — uvicorn entry for the bundle)
│   ├── maximobrd-backend.spec         (PyInstaller build spec — Milestone 3)
│   ├── config.py                      (cross-platform app-data dir; frozen-aware paths)
│   ├── routes/
│   │   ├── __init__.py               (api_error() helper — shared error envelope)
│   │   ├── projects.py
│   │   ├── sources.py
│   │   ├── pipeline.py
│   │   └── settings.py
│   ├── services/
│   │   ├── llm_client.py
│   │   ├── docx_renderer.py
│   │   ├── progress_bus.py
│   │   ├── keystore.py               (macOS Keychain wrapper via keyring)
│   │   └── structure_extractor.py    (branded-template heading extraction)
│   ├── agents/
│   │   ├── runner.py                 (pipeline orchestrator — BackgroundTask entry point)
│   │   ├── extractor.py
│   │   ├── summarizer.py
│   │   ├── analyzer.py
│   │   └── generator.py
│   ├── processors/
│   │   ├── __init__.py               (classify/is_extractable/extract_text/embedded_date dispatch)
│   │   ├── pdf.py, docx.py, xlsx.py, plaintext.py
│   │   ├── filedates.py              (embedded created/modified dates from PDF/DOCX/XLSX metadata)
│   │   └── (audio.py, video.py, image.py — Milestone 5)
│   ├── models/
│   │   ├── project.py, pipeline.py, settings.py
│   ├── db/
│   │   ├── database.py
│   │   └── models.py                 (SQLAlchemy ORM tables)
│   ├── prompts/
│   │   ├── summarizer.txt
│   │   ├── analyzer_system.txt
│   │   ├── analyzer_user.txt
│   │   ├── generator_system.txt
│   │   └── generator_user.txt
│   ├── templates/
│   │   └── brd_default_structure.json
│   ├── tests/
│   │   ├── conftest.py               (redirects app data + project dirs to tmp for tests)
│   │   ├── test_processors.py
│   │   ├── test_id_assignment.py
│   │   ├── test_docx_renderer.py
│   │   ├── test_llm_client.py
│   │   ├── test_settings.py
│   │   ├── test_structure_extractor.py
│   │   ├── test_branding.py
│   │   ├── test_filedates.py
│   │   └── test_pipeline_integration.py
│   └── requirements.txt
├── knowledge/versions/
│   ├── maximo-76.md
│   ├── mas-9.md
│   └── mas-8.md                      (Milestone 5)
├── electron/                         (Milestone 3 — desktop shell)
│   ├── main.js                       (spawn backend, health-gate, window, lifecycle)
│   ├── preload.js                    (minimal secure bridge; contextIsolation on)
│   └── package.json                  (electron + electron-builder config → DMG)
├── release/                          (built DMG/zip output — gitignored)
├── docs/
│   ├── blueprint.md
│   └── implementation-spec.md        (this document)
└── package.json                      (root convenience scripts)
```

### Backend dependencies (MVP — confirm before installing)

`fastapi`, `uvicorn`, `sqlalchemy`, `pydantic`, `python-multipart`, `aiofiles`, `python-docx`, `pymupdf`, `openpyxl`, `anthropic`, `keyring`, `pytest` (dev).

---

## 7. Prerequisites (Create Before Coding)

### 7.1 `backend/templates/brd_default_structure.json`

```json
{
  "version": "1.0",
  "sections": [
    { "id": "cover", "title": "Document Control", "level": 1, "required": true },
    { "id": "executive_summary", "title": "Executive Summary", "level": 1, "required": true },
    { "id": "background", "title": "Background and Objectives", "level": 1, "required": true },
    { "id": "scope", "title": "Scope", "level": 1, "required": true },
    { "id": "scope_in", "title": "In Scope", "level": 2, "required": true },
    { "id": "scope_out", "title": "Out of Scope", "level": 2, "required": true },
    { "id": "assumptions", "title": "Assumptions", "level": 1, "required": true },
    { "id": "requirements", "title": "Business Requirements", "level": 1, "required": true },
    { "id": "non_functional", "title": "Non-Functional Requirements", "level": 1, "required": false },
    { "id": "integrations", "title": "Integration Requirements", "level": 1, "required": false },
    { "id": "risks", "title": "Implementation Risks", "level": 1, "required": true },
    { "id": "appendix", "title": "Appendix — Source Documents", "level": 1, "required": true }
  ]
}
```

### 7.2 Maximo version mapping

| UI label | `maximo_version` key | Knowledge file | MVP |
|----------|----------------------|----------------|-----|
| Maximo 7.6.0.x | `maximo-760` | `maximo-76.md` | Enabled |
| Maximo 7.6.1.x | `maximo-761` | `maximo-76.md` | Enabled |
| MAS 8.x | `mas-8` | `mas-8.md` | Disabled ("Coming soon") |
| MAS 9.x | `mas-9` | `mas-9.md` | Enabled |

### 7.3 Knowledge file minimum content

Each `knowledge/versions/*.md` must include these H2 sections — content is injected verbatim into analyzer/generator system prompts; never hardcode version facts in Python:

- Platform Overview
- Deployment Model
- Customization Mechanisms (MBO, automation scripts, etc.)
- Integration Patterns
- Native vs Custom — decision guidance
- Common Module Capabilities (WO, ASSET, INV, PURCH, PM, SR)
- Upgrade / Migration Considerations
- Known Platform Limitations

Stubs are acceptable for Milestone 0–1 bring-up; full prose is a parallel content task that must be done before real client use.

### 7.4 AI providers and default models

| Provider | Default `model_id` | Models docs link (shown in Settings) |
|----------|-------------------|--------------------------------------|
| `anthropic` | `claude-sonnet-4-6` | https://platform.claude.com/docs/en/about-claude/models/overview |
| `openai` | `gpt-4o` | https://platform.openai.com/docs/models |

The model field is free text — users can enter any model name their provider offers; the Settings page links to each provider's model list. Provider metadata (label, default model, docs URL) lives in `backend/config.py` `PROVIDERS` and is served to the UI by `GET /settings/provider`, so adding a provider is a backend-only change.

### 7.5 Maximo module codes (for `BRD-{MODULE}-{NNN}`)

Allowed `MODULE` values:

```
WO, ASSET, INV, PURCH, PM, SR, LABOR, CAL, BUDGET, METER, ROUTES, SLA, LOC, PERSON, COMP, SAFETY, CONTRACT, RFQ, REORDER, GL, ESCALATION, KPI, MOBILE, INTEGRATION, GENERAL
```

ID assignment (deterministic, post-LLM):

- Group requirements by `module`.
- Sort by `sort_order` from LLM (fallback: original list order).
- Assign `BRD-{MODULE}-001`, `BRD-{MODULE}-002`, … per module.

---

## 8. Source Processing State Machine

```
                    ┌─────────────┐
         upload     │  UPLOADED   │  (file on disk)
        ──────────► │             │
                    └──────┬──────┘
                           │ auto-extract (text types)
                    ┌──────▼──────┐
                    │ EXTRACTING  │
                    └──────┬──────┘
              success      │      failure
         ┌─────────────────┼─────────────────┐
         ▼                 │                 ▼
  ┌─────────────┐          │          ┌─────────────┐
  │  EXTRACTED  │          │          │    ERROR    │
  └─────────────┘          │          └─────────────┘
                           │
              (audio/video/image — until Milestone 5)
                    ┌──────▼──────┐
                    │   PENDING   │  "Processing available in a later release"
                    └─────────────┘
```

**Rules:**

- `POST /generate` requires ≥1 source with `processing_status = EXTRACTED`.
- Pipeline Stage 1 reads from `extracted/{source_id}.txt`; re-extracts only if sidecar missing.
- `PENDING` and `ERROR` sources are skipped in pipeline with logged warnings.

### File type classification

| Extensions | `filetype` | Upload status | Extract on upload |
|------------|------------|---------------|-------------------|
| pdf | `pdf` | UPLOADED → EXTRACTING | Yes |
| docx | `docx` | UPLOADED → EXTRACTING | Yes |
| txt, md | `plaintext` | UPLOADED → EXTRACTING | Yes |
| xlsx, xls | `spreadsheet` | UPLOADED → EXTRACTING | Yes |
| mp3, wav, m4a, ogg | `audio` | PENDING | No (Milestone 5) |
| mp4, mov, webm | `video` | PENDING | No (Milestone 5) |
| png, jpg, jpeg, webp | `image` | PENDING | No (Milestone 5) |
| other | `unknown` | ERROR | No — error message set |

---

## 9. Data Models

### 9.1 Database — single `app.db` (MVP)

One SQLite file in the OS app-data dir. All per-project tables carry `project_id`, so splitting into a portable per-project `project.db` in Milestone 3 is a data move, not a redesign.

**`projects`**

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| client_name | TEXT | |
| project_name | TEXT | |
| project_date | DATE | |
| maximo_version | TEXT | key from §7.2 |
| folder_path | TEXT UNIQUE | absolute path |
| branded_docx_path | TEXT NULL | used from Milestone 2 |
| created_at / updated_at | DATETIME | |

**`sources`**

| Column | Type |
|--------|------|
| id | UUID PK |
| project_id | UUID FK |
| filename | TEXT |
| filepath | TEXT |
| filetype | TEXT |
| file_size_bytes | INTEGER |
| source_timestamp | DATETIME |
| user_timestamp_override | DATETIME NULL |
| processing_status | TEXT |
| error_message | TEXT NULL |
| extracted_text_path | TEXT NULL |
| char_count | INTEGER NULL |
| created_at | DATETIME |

**`pipeline_runs`**

| Column | Type |
|--------|------|
| id | UUID PK |
| project_id | UUID FK |
| status | TEXT (`RUNNING`, `DONE`, `FAILED`, `CANCELLED`) |
| started_at | DATETIME |
| completed_at | DATETIME NULL |
| output_path | TEXT NULL |
| error_message | TEXT NULL |
| sources_used_count | INTEGER |
| skipped_sources_count | INTEGER |

**`provider_settings`** (singleton row `id=1`)

| Column | Type | Notes |
|--------|------|-------|
| id | INT PK | always 1 |
| provider | TEXT | `anthropic` (MVP) |
| model_id | TEXT | |
| updated_at | DATETIME | |

The API key is **not** a column anywhere. It lives in the macOS Keychain under service `maximobrd`, account `api_key` (and under Electron `safeStorage` from Milestone 3).

### 9.2 Pydantic — pipeline contracts (`backend/models/pipeline.py`)

```python
# Requirement (pre-ID assignment from LLM)
class RequirementDraft(BaseModel):
    module: str                    # must match allowed MODULE list
    title: str
    description: str
    requirement_type: Literal["functional", "non_functional", "configuration", "integration"]
    priority: Literal["high", "medium", "low"]
    source_ref: str                # filename only
    source_timestamp: str          # ISO 8601
    sort_order: int
    notes: str | None = None

# After ID assignment
class Requirement(BaseModel):
    id: str                        # BRD-WO-001
    module: str
    title: str
    description: str
    requirement_type: str
    priority: str
    source_ref: str
    source_timestamp: str
    notes: str | None = None

class ExtractedSource(BaseModel):
    source_id: str
    filename: str
    timestamp: datetime
    raw_text: str
    char_count: int
    page_count: int | None = None

class SummarizedSource(BaseModel):
    source_id: str
    filename: str
    timestamp: datetime
    content: str                   # full text or summary
    was_summarized: bool

class AnalysisDraft(BaseModel):
    """Schema passed to the LLM for analysis — contains RequirementDraft items (no IDs)."""
    requirements: list[RequirementDraft]
    modules_referenced: list[str]
    analysis_notes: str | None = None

class AnalysisResult(BaseModel):
    """Post-processing result after assign_ids() converts drafts to full Requirement objects."""
    requirements: list[Requirement]
    modules_referenced: list[str]
    analysis_notes: str | None = None

class NarrativeSection(BaseModel):
    section_id: str                # matches brd_default_structure id
    title: str
    body: str                      # plain text, paragraphs separated by \n\n

class NarrativeSet(BaseModel):
    """Schema passed to the LLM for generation — returned before assembly into BRDDocument."""
    narratives: list[NarrativeSection]

class BRDDocument(BaseModel):
    project_metadata: dict         # client, project, date, maximo_version
    structure: list[dict]          # ordered sections from template (or branded DOCX, M2+)
    narratives: list[NarrativeSection]
    requirements: list[Requirement]
    appendix_sources: list[str]    # unique filenames used
```

### 9.3 Requirement table columns (DOCX)

Each module subsection under "Business Requirements" renders one `python-docx` Table:

| Column | Width ratio |
|--------|-------------|
| Requirement ID | 15% |
| Title | 20% |
| Description | 35% |
| Type | 10% |
| Priority | 10% |
| Source Document | 10% |

Header row: bold. All cells: Normal style (no inline fonts).

---

## 10. API Contract

Base URL: `http://127.0.0.1:8765` (port from `MAXIMOBRD_PORT`, default 8765)
All errors: `{ "error": { "code": "STRING", "message": "Human readable" } }`
Never return Python stack traces to the client. Request-validation failures (FastAPI 422) are wrapped in the same envelope with code `VALIDATION`.

### 10.1 Health

`GET /health` → `200` `{ "status": "ok", "version": "0.1.0" }`

### 10.2 Projects

`POST /projects`

```json
{
  "client_name": "Acme Corp",
  "project_name": "EAM Upgrade",
  "project_date": "2026-06-01",
  "maximo_version": "mas-9",
  "folder_path": "/Users/consultant/MaximoBRD/acme-eam"
}
```

`folder_path` is optional — defaults to `~/MaximoBRD/{client-slug}-{project-slug}`. Response `201` returns the full project object. Side effects: create `sources/`, `extracted/`, `output/` subfolders; insert row.

- `GET /projects` → `200` list.
- `GET /projects/{id}` → `200` full project + source count + latest run.
- `DELETE /projects/{id}` → `204` (removes DB rows only; never deletes the folder).
- `PUT /projects/{id}/branding` — multipart branded DOCX → `branding/reference.docx`, updates `branded_docx_path`, returns extracted heading preview (422 `INVALID_TEMPLATE` if not a .docx or it has no Heading 1–3).
- `GET /projects/{id}/branding` → `{ branded_docx_path, headings }` — preview for the stored template (empty when none set).
- `DELETE /projects/{id}/branding` → `204` — removes the reference file and reverts to the default structure.

### 10.3 Sources

`POST /projects/{id}/sources/upload`

- `multipart/form-data`: `file` (binary), optional `source_timestamp` (ISO), optional `user_timestamp_override` (ISO).
- Filename collision: append `_{n}` before extension (`workshop.pdf` → `workshop_1.pdf`).
- Max size 500 MB (`MAX_UPLOAD_BYTES`); streamed to disk via `aiofiles`, never fully buffered in RAM.
- Effective-date precedence: the file's **embedded metadata date** (PDF `modDate`/`creationDate`, DOCX/XLSX core-properties `modified`/`created` — read by `processors/filedates.py`, modified preferred over created) → browser-reported file modified time (`source_timestamp` form field) → upload time. Embedded dates survive email downloads, which reset filesystem mtime; plain text and media have no embedded date and use the fallbacks.
- Extraction runs as a `BackgroundTask` immediately after upload.

Response `201`:

```json
{
  "id": "uuid",
  "filename": "workshop.pdf",
  "filetype": "pdf",
  "file_size_bytes": 1048576,
  "processing_status": "EXTRACTING",
  "source_timestamp": "2026-05-15T09:00:00Z"
}
```

- `GET /projects/{id}/sources` → `200` array (UI refreshes this after upload and while badges show `EXTRACTING`-at-upload-time only; no pipeline polling).
- `DELETE /projects/{id}/sources/{source_id}` → `204` (file + sidecar + row).
- `PATCH /projects/{id}/sources/{source_id}` → `{ "user_timestamp_override": "2026-05-10T14:00:00Z" }`.
- `POST /projects/{id}/sources/refresh-dates` → `200` refreshed source array — re-reads each file's embedded metadata date from disk; where one is found it updates `source_timestamp` **and clears any `user_timestamp_override`** (the user is explicitly asking for the files' real dates). Sources without an embedded date (plain text, media) keep their current date and override. UI exposes this as "Re-read dates from files" under the sources table.

### 10.4 Settings

MVP key flow (no Electron yet): keys pass through one POST over localhost, are written straight to the macOS Keychain (one entry per provider, account `api_key_{provider}`), and are never persisted or logged anywhere else.

- `GET /settings/provider` → `200`

```json
{
  "provider": "anthropic",
  "model_id": "claude-sonnet-4-6",
  "configured": true,
  "providers": [
    { "key": "anthropic", "label": "Anthropic Claude", "default_model": "claude-sonnet-4-6",
      "models_url": "https://platform.claude.com/docs/en/about-claude/models/overview", "configured": true },
    { "key": "openai", "label": "OpenAI", "default_model": "gpt-4o",
      "models_url": "https://platform.openai.com/docs/models", "configured": false }
  ]
}
```

- `POST /settings/provider` → `{ "provider": "openai", "model_id": "gpt-4o" }` (blank `model_id` falls back to the provider default).
- `POST /settings/api-key` → `{ "provider": "anthropic", "api_key": "sk-ant-..." }` → stored via `keyring`; response `{ "success": true }`. Key is masked in the UI after save.
- `DELETE /settings/api-key/{provider}` → removes that provider's key from the Keychain.
- `POST /settings/provider/test` → body `{ "provider"?, "model_id"?, "api_key"? }` — all optional. Tests **what the Settings form currently shows**: the given provider/model (falling back to saved settings), and the given key (falling back to that provider's Keychain entry; a typed key is tested without being stored). Makes a minimal completion ("Reply OK") → `{ "success": true, "latency_ms": 842 }`.

From Milestone 3 this migrates to the safeStorage + `X-API-Key` header-injection design in §13.3.

### 10.5 Pipeline

`POST /projects/{id}/generate`

- Validates: provider configured (key in Keychain), ≥1 `EXTRACTED` source.
- Creates `pipeline_runs` row `status=RUNNING`, starts background pipeline task.
- Returns `202` `{ "run_id": "uuid", "status": "RUNNING" }`.

- `GET /pipeline/{run_id}` → run metadata.
- `GET /pipeline/{run_id}/stream` — SSE (§11).
- `POST /pipeline/{run_id}/cancel` → `202` `{ "run_id", "status": "CANCELLING" }` — sets the cancel flag on the ProgressBus; the pipeline checks it between stages, then marks the run `CANCELLED` and emits an `error` SSE event with `stage: "cancelled"`. `409 NOT_RUNNING` if the run already finished.
- `GET /pipeline/{run_id}/download` → DOCX stream with `Content-Disposition: attachment` (browser saves it; native save dialog arrives with Electron).
- `GET /projects/{id}/runs` → list of past runs.

---

## 11. SSE Event Specification

`GET /pipeline/{run_id}/stream` — `Content-Type: text/event-stream`, fed by the in-memory ProgressBus.

```
event: progress
data: {"stage":"extraction","step":null,"message":"Processing workshop.pdf","percent":12,"run_id":"..."}

event: progress
data: {"stage":"analysis","step":"summarizing","message":"Summarizing requirements.xlsx","percent":42,"run_id":"..."}

event: done
data: {"stage":"done","output_path":"/path/to/output/uuid.docx","percent":100,"run_id":"..."}

event: error
data: {"stage":"failed","message":"Analysis validation failed","percent":0,"run_id":"..."}

event: error
data: {"stage":"cancelled","message":"Generation cancelled","percent":0,"run_id":"..."}
```

A cancelled run uses the `error` event type with `stage: "cancelled"` so the UI can distinguish a cancel from a failure.

| stage | percent range |
|-------|---------------|
| extraction | 0–30 |
| analysis / summarizing | 30–55 |
| analysis / extracting | 55–75 |
| generation | 75–90 |
| rendering | 90–100 |
| done | 100 |
| failed | — |

Stream closes after `done` or `error`. If the client connects after the run finished, replay the stored events then close. Reconnect logic: not required for MVP.

---

## 12. Pipeline Implementation Detail

### 12.1 Pre-flight

1. Load project row.
2. Load knowledge: `VERSION_MAP[maximo_version]` → read `.md` file.
3. Load BRD structure: if `branded_docx_path` is set and the file exists → `StructureExtractor.extract_headings()`; else `brd_default_structure.json`. Branded headings matching known BRD sections get canonical ids (so requirement tables and the appendix land in the right place); unrecognised headings get slug ids and render as narrative sections.
4. Load sources where `processing_status == EXTRACTED`, ordered by effective timestamp (`user_timestamp_override ?? source_timestamp`).
5. Read API key from Keychain (M3+: from `X-API-Key` header).

### 12.2 Stage 1 — Extractor (`agents/extractor.py`)

For each eligible source:

1. Read `extracted/{source_id}.txt` if it exists and is non-empty.
2. Else dispatch processor, write sidecar, update DB.
3. Build `ExtractedSource`.
4. Emit SSE per file.

### 12.3 Stage 2a — Summarizer (`agents/summarizer.py`)

Runs only for sources with `char_count > TOKEN_THRESHOLD` (default 12 000 chars).

**Prompt** (`prompts/summarizer.txt`):

```
You are compressing source material for a Maximo BRD analysis pass.

Source filename: {filename}
Source timestamp: {timestamp}

Preserve:
- All explicit requirements, decisions, and constraints
- Named Maximo modules and applications referenced
- Integration points, data entities, and process flows
- Numbers, dates, SLAs, and priorities

Remove:
- Boilerplate, repeated headers/footers, page numbers
- Filler narrative unrelated to requirements

Output a structured excerpt under 8000 characters. Begin with:
SOURCE: {filename}
DATE: {timestamp}
---
[excerpt]
```

### 12.4 Stage 2b — Analyzer (`agents/analyzer.py`)

**System prompt** (`prompts/analyzer_system.txt`):

```
You are a senior IBM Maximo consultant extracting business requirements.

Use ONLY the Maximo version knowledge provided below. Do not assume features not supported by that version.

{maximo_knowledge}

Rules:
- Distinguish configuration vs customization
- Flag implied requirements explicitly
- Group by Maximo module
- Each requirement MUST cite source_ref (filename only) and source_timestamp
- Use requirement_type: functional | non_functional | configuration | integration
- Use priority: high | medium | low
- module must be one of: {module_list}
- Do NOT assign BRD IDs — assign sort_order integers starting at 1 per module

Output valid JSON matching the provided schema.
```

**User prompt** (`prompts/analyzer_user.txt`):

```
Project: {project_name} for {client_name}
Maximo version: {maximo_version_label}
BRD sections to populate: {section_list}

Sources (chronological):
{sources_json}

Extract all business requirements from these sources.
```

`complete_json()` schema = `AnalysisDraft` (contains `RequirementDraft` items — no `id` field). Post-process via `assign_ids()`: assign `BRD-{MODULE}-{NNN}` IDs per §7.5, producing an `AnalysisResult` with full `Requirement` objects.

### 12.5 Stage 3a — Generator (`agents/generator.py`)

**System prompt** (`prompts/generator_system.txt`):

```
You are writing consultant-grade BRD narrative sections for an IBM Maximo engagement.

Use the Maximo version knowledge:
{maximo_knowledge}

Write clear, professional prose. No bullet lists in narrative sections unless the section is Assumptions or Risks.
```

**User prompt** (`prompts/generator_user.txt`):

```
Project metadata: {metadata_json}
BRD structure: {structure_json}
Extracted requirements: {requirements_json}

Generate narrative body text for these sections:
- executive_summary
- background
- scope_in
- scope_out
- assumptions
- risks

Each narrative section must reference relevant modules and highlight version-specific considerations.
```

`complete_json()` schema = `NarrativeSet` (just the narrative sections). Post-process: assemble into `BRDDocument` by combining narratives, requirements, metadata, structure, and appendix.

### 12.6 Stage 3b — DocxRenderer (`services/docx_renderer.py`)

1. Create blank Document.
2. Add DRAFT watermark via header XML injection (not text box).
3. For each structure section in order:
   - Heading 1/2/3 based on level.
   - If section id = `requirements`: group by module, Heading 2 per module, Table per module (§9.3).
   - If narrative section: render paragraphs as Normal.
4. Appendix: bullet list of source filenames.
5. Save to `{folder}/output/{run_id}.docx`.

Named Word styles only — no inline fonts (visual branding clone is Milestone 6).

### 12.7 LLMClient (`services/llm_client.py`)

```python
class LLMClient:
    def __init__(self, api_key: str, model_id: str, provider: str = "anthropic"): ...
    def complete(self, messages: list[dict], max_tokens: int = 4096, system: str | None = None) -> str: ...
    def complete_json(self, messages: list[dict], schema: type[BaseModel], max_tokens: int = 8192, system: str | None = None) -> BaseModel: ...
```

- 3 retries, exponential backoff from 2 s — shared across providers (both SDKs raise identically named exception classes).
- Anthropic: `messages.create`; JSON via tool use (the Pydantic schema becomes the tool's `input_schema`; `tool_choice` forces the model to call it).
- OpenAI: `chat.completions.create`; JSON via `response_format={"type": "json_object"}` with the schema embedded in the system message.
- `complete_json()` returns the validated `BaseModel` instance directly (not a raw `dict`).
- On Pydantic validation failure: retry once with a "fix this JSON to match the schema" prompt, then raise `LLMError`.
- Only file importing the `anthropic` / `openai` SDKs. Milestone 7 adds Ollama behind the same two methods.

---

## 13. Electron Shell (Milestone 3 — as built)

> **Design choice:** the original plan routed every API call through an Electron IPC
> bridge so it could inject API keys from `safeStorage`. We took a simpler path. Since
> FastAPI already serves the SPA at `/`, the window loads the backend's own URL and the
> renderer is **same-origin** with the API — `fetch`, SSE, and uploads work as-is, with
> **no IPC bridge and no `api.js` changes**. Keys stay in the OS credential store via
> `keyring`, so no key-migration plumbing is needed either. Less code, fewer moving parts.

### 13.1 The shell (`electron/main.js`, `electron/preload.js`)

`main.js` owns the whole lifecycle: pick a free TCP port → spawn the backend with
`MAXIMOBRD_PORT` set → poll `GET /health` (500 ms interval, 30 s ceiling) → open a
`BrowserWindow` at `http://127.0.0.1:<port>/`. External links (e.g. provider model-docs)
open in the user's real browser via `shell.openExternal`. On quit the backend child gets
SIGTERM, then SIGKILL after a 5 s grace.

`preload.js` is intentionally tiny — `contextIsolation: true`, `nodeIntegration: false`,
exposing only a read-only `window.maximobrd = { isDesktop, platform }`. No `api:*`,
`storage:*`, or `dialog:*` channels: Chromium's own drag-drop, `<input type=file>`, and
`<a download>` cover the file interactions for now (native dialogs are deferred polish).

Run modes (chosen in `main.js`):

| Mode | Backend source |
|------|----------------|
| Packaged (`app.isPackaged`) | PyInstaller binary at `resources/backend/maximobrd-backend` |
| `npm run dev:electron` | the backend venv's `python run_server.py` |
| `BACKEND_DEV=1` | reuse an externally running uvicorn (no spawn) — for `--reload` dev |

### 13.2 Key storage

Unchanged from the MVP: the spawned backend reads the API key from `keyring`, which
selects the correct OS store automatically (macOS Keychain / Windows Credential Locker /
Linux Secret Service). No `safeStorage`, no header injection, no migration step.

### 13.3 Backend bundling (`backend/maximobrd-backend.spec`)

PyInstaller **onedir** build of `run_server.py`. The spec bundles every runtime data
file so the binary is self-contained: `prompts/`, `templates/`, `knowledge/versions/`,
and the built `frontend/dist/` (served at `/` as `frontend_dist`). `collect_all` pulls
in the parts static analysis misses — `keyring` OS backends, the `anthropic`/`openai`
SDK data, PyMuPDF's native lib, and uvicorn's protocol modules — plus the SQLAlchemy
sqlite dialect. `config.py` resolves these paths from `sys._MEIPASS` when `sys.frozen`.

### 13.4 Packaging (`electron/package.json` → electron-builder)

electron-builder copies `backend/dist/maximobrd-backend/` into the app's
`Contents/Resources/backend/` (`extraResources`) and produces a macOS **DMG** + zip in
`release/`. A `win` (NSIS) target is configured but must be built on Windows (PyInstaller
can't cross-compile). Internal distribution — unsigned, no notarization yet, so first
launch needs right-click → Open to clear Gatekeeper.

Build: `npm run build:mac` (frontend build → PyInstaller backend → electron-builder DMG).

---

## 14. UI Specification

### 14.1 Navigation

```
/                       → ProjectList
/projects/:id           → ProjectDetail
/projects/:id/generate  → Generate (pipeline progress)
/settings               → Settings
```

No HTML `<form>` tags (React `onClick`/`onChange` only). No localStorage/sessionStorage — server state lives in the backend; UI state in Zustand.

### 14.2 ProjectList

- Table: client, project name, date, Maximo version, created.
- "New Project" modal: client_name (required), project_name (required), project_date (default today), maximo_version (select; `mas-8` disabled with tooltip), folder path (text input pre-filled with the default path; native folder picker arrives with Electron).
- Empty state: "Create your first project".
- First-run gate: if provider not configured, banner linking to Settings.

### 14.3 ProjectDetail

1. **Project metadata** (read-only header).
2. **Sources** — drag-drop zone + browse button. Columns: filename, size, effective date, status badge, actions (delete, edit date). Badges: Extracting, Ready (EXTRACTED), Pending, Error (tooltip with message).
3. **Generate** button — disabled unless ≥1 EXTRACTED source AND provider configured.
4. **Run history** — past runs with status, date, download link.
5. **Branded template** — upload/replace/remove a reference DOCX with an indented heading preview (Milestone 2).

### 14.4 Generate page

- Progress bar (0–100) driven by SSE.
- Stage checklist: Extraction → Analysis → Generation → Rendering.
- Live message log (last 5 messages).
- On `done`: "Download BRD" (browser download; native save dialog in Milestone 3).
- On `error`: message + "Return to project" + "Retry".
- Cancel button while running ("Cancelling…" until the pipeline reaches a stage boundary); cancelled state shows Retry + "Return to project" (Milestone 2).

### 14.5 Settings

- Provider radio: Anthropic Claude | OpenAI (rendered from `GET /settings/provider` → `providers`, so Ollama appears automatically in Milestone 7). A "key saved" badge shows per provider.
- Model: free-text input pre-filled with the provider default, with a hyperlink to that provider's model-list docs page (`models_url`).
- API key password field per provider → `POST /settings/api-key`; shown masked once configured; each provider keeps its own Keychain entry.
- Test Connection button (tests the saved provider/model); Save button.

---

## 15. Configuration (`backend/config.py`)

| Variable | Default | Purpose |
|----------|---------|---------|
| `MAXIMOBRD_PORT` | `8765` | Free port chosen by the Electron shell at launch; fixed in dev |
| `TOKEN_THRESHOLD` | `12000` | Chars before summarization |
| `MAX_UPLOAD_BYTES` | `524288000` | 500 MB |
| `LLM_MAX_TOKENS_SUMMARIZE` | `4096` | |
| `LLM_MAX_TOKENS_ANALYZE` | `8192` | |
| `LLM_MAX_TOKENS_GENERATE` | `8192` | |
| `APP_DATA_DIR` | OS-specific (macOS/Windows/Linux) | `app.db` location — cross-platform default |
| `PROJECTS_DEFAULT_DIR` | `~/MaximoBRD` | Default project folder root |
| `MAXIMOBRD_FRONTEND_DIST` | bundled / `frontend/dist` | Override for the built UI served at `/` (M3) |

---

## 16. Local Development Setup

### 16.1 Prerequisites

Node 20+, Python 3.11+, npm.

### 16.2 First-time setup

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

### 16.3 Run (two terminals)

```bash
# Terminal 1 — Backend
cd backend && source .venv/bin/activate
uvicorn main:app --reload --port 8765

# Terminal 2 — Frontend (Vite proxies /api → 8765)
cd frontend && npm run dev
```

Open `http://localhost:5173`. Single-command alternative once stable: `npm run build` in `frontend/`, then FastAPI serves `frontend/dist/` at `/` — one terminal, one URL.

### 16.4 Root `package.json` scripts

```json
{
  "scripts": {
    "dev:backend":    "cd backend && .venv/bin/uvicorn main:app --reload --port 8765 --host 127.0.0.1",
    "dev:frontend":   "cd frontend && npm run dev",
    "build:frontend": "cd frontend && npm run build",
    "test:backend":   "cd backend && .venv/bin/python -m pytest tests/ -q",
    "app":            "npm run build:frontend && npm run dev:backend",
    "dev:electron":   "npm run build:frontend && cd electron && npm start",
    "build:backend":  "npm run build:frontend && cd backend && .venv/bin/python -m PyInstaller --noconfirm maximobrd-backend.spec",
    "build:mac":      "npm run build:backend && cd electron && npm run dist"
  }
}
```

`app` is the single-command browser mode: builds the frontend into `dist/`, then the FastAPI server serves it at `http://127.0.0.1:8765` — one terminal, one URL.

Milestone 3 scripts: `dev:electron` runs the desktop shell against the dev venv backend (no packaging); `build:backend` produces the PyInstaller bundle; `build:mac` produces the DMG in `release/`.

---

## 17. Testing Strategy

### 17.1 Unit tests (pytest)

| Module | Tests | Status |
|--------|-------|--------|
| `processors/pdf.py` | sample PDF → non-empty text | ✅ `test_processors.py` |
| `processors/docx.py` | paragraphs + tables | ✅ `test_processors.py` |
| ID assignment | `BRD-WO-001` sequencing | ✅ `test_id_assignment.py` |
| `docx_renderer.py` | tables exist, DRAFT header present, named styles only | ✅ `test_docx_renderer.py` |
| `llm_client.py` | retry logic (mocked) | ✅ `test_llm_client.py` |
| `structure_extractor.py` | heading hierarchy order, canonical id mapping | ✅ `test_structure_extractor.py` |
| `processors/filedates.py` | PDF date-string parsing (offsets/partials), DOCX/XLSX core properties, unreadable file → None | ✅ `test_filedates.py` |

### 17.2 Integration tests

- Create project → upload TXT → wait EXTRACTED → generate (mock LLM) → DOCX file exists. ✅ `test_pipeline_integration.py`
- Generate blocked when no EXTRACTED sources. ✅ `test_pipeline_integration.py`
- Malformed PDF → ERROR status + message. ✅ `test_pipeline_integration.py`
- Cancel flag → run CANCELLED + `stage: "cancelled"` SSE event; cancel after finish → 409. ✅ `test_pipeline_integration.py`
- SSE replay for late connections (in-memory replay + post-restart synthesis). ✅ `test_pipeline_integration.py`
- Generate with a branded template → DONE. ✅ `test_pipeline_integration.py`
- Validation errors use the `{error: {code, message}}` envelope. ✅ `test_pipeline_integration.py`
- Branding upload/preview/removal routes; non-DOCX and heading-less templates rejected. ✅ `test_branding.py`
- Upload uses embedded document date over browser-reported time; plain text falls back. ✅ `test_pipeline_integration.py`
- `refresh-dates` backfills stored dates from file metadata and preserves manual overrides. ✅ `test_pipeline_integration.py`

### 17.3 Manual E2E (Milestone 1 exit criteria)

1. Real Claude key configured via Settings.
2. Upload 1 PDF + 1 DOCX (+ 1 MP3 to confirm PENDING doesn't break anything).
3. Generate BRD; watch SSE progress.
4. Open DOCX in Word: headings correct, requirement tables present, DRAFT watermark visible, IDs formatted `BRD-*-NNN`, source filenames cited.
5. Confirm no API key appears in `app.db` or backend logs.

---

## 18. Milestone Plan

### Milestone 0 — Scaffold ✅ Complete

- [x] Repo scaffold: `backend/` (FastAPI + `/health`), `frontend/` (Vite + React + Tailwind + router shell)
- [x] React page fetches and displays `/health` through the Vite proxy
- [x] Create prerequisite artifacts: `brd_default_structure.json`, prompt files (§12), stub `maximo-76.md` + `mas-9.md`
- [x] `keyring` round-trip smoke test (write/read/delete a dummy value in Keychain)

### Milestone 1 — Working MVP ✅ Complete

*Week 1 — data path:*

- [x] SQLite schema (§9.1) + `create_all` on startup
- [x] Project CRUD routes + ProjectList/ProjectDetail UI
- [x] Streaming upload endpoint + all four text processors + background extraction + status badges
- [x] Media files stored as PENDING; unknown types → ERROR

*Week 2 — AI path:*

- [x] Settings routes + Keychain storage + Settings page + Test Connection
- [x] `LLMClient` (Anthropic) with retries + JSON-via-tool-use
- [x] Pipeline: pre-flight, 4 agents, ProgressBus, SSE stream, run row lifecycle
- [x] `DocxRenderer` per §12.6 + download endpoint + Generate page

**Also delivered:** `agents/runner.py` (pipeline orchestrator), `services/keystore.py` (Keychain wrapper), `routes/__init__.py` (error envelope helper), `frontend/src/api.js` (single API layer), `frontend/src/components/StatusBadge.jsx`, and four pytest test files (processors, ID assignment, DOCX renderer, full pipeline integration with mocked LLM).

### Milestone 2 — Hardening + spec completion ✅ Complete

- [x] Cancel pipeline (ProgressBus flag checked between stages, `CANCELLED` status, `POST /pipeline/{run_id}/cancel`) + Retry flow for failed and cancelled runs
- [x] Branded DOCX upload (`PUT/GET/DELETE /projects/{id}/branding`) + `StructureExtractor` heading preview + use in pre-flight
- [x] Timestamp override UI (inline date editor per source row, with clear-override); filename collision and corrupt-file handling verified by tests
- [x] Structured API errors everywhere (validation 422s wrapped in the envelope); React error boundary around all routes
- [x] Unit + integration tests per §17.1–17.2; SSE replay for late connections covered by tests
- [ ] ~~Optional: introduce Alembic~~ — skipped: no schema churn yet and it would add a dependency; revisit at the Milestone 3 DB split

**Done when:** the app survives bad inputs gracefully and the test suite is green. *(Met — 43 backend tests passing.)*

### Milestone 3 — Desktop shell ✅ Complete

- [x] `electron/` package: `main.js` + minimal secure `preload.js` (§13.1)
- [x] **Same-origin** instead of an IPC bridge — window loads the backend URL, so `src/api.js`, fetch, SSE, and uploads are unchanged (§13)
- [x] Dynamic free port + `/health` gate + child-process lifecycle (SIGTERM→SIGKILL)
- [x] Cross-platform backend: OS-specific `APP_DATA_DIR`, frozen-aware resource paths, `run_server.py` launcher
- [x] PyInstaller self-contained backend bundle (`maximobrd-backend.spec`) + electron-builder **macOS DMG**; verified the packaged app spawns the backend, health-gates, and shuts it down cleanly
- [x] ~~safeStorage key migration~~ — **declined**: kept `keyring` (already cross-platform incl. Windows); the same-origin shell needs no header injection
- [x] ~~Native file/folder/save dialogs~~ — deferred (Chromium drag-drop / `<input file>` / `<a download>` suffice); Milestone 8
- [x] ~~Portable per-project `project.db` split~~ — deferred: kept the single shared `app.db` (rows already keyed by `project_id`)

**Done:** `npm run build:mac` produces a double-click DMG; the packaged app launches the bundled backend on a dynamic port and serves the full UI with no terminal and no Python install. *(Windows installer is a build-on-Windows follow-up — Milestone 8.)*

### Milestone 4 — Second provider ✅ (pulled forward, completed with Milestone 1)

- [x] OpenAI branch in `LLMClient` (`response_format=json_object`, schema in system message)
- [x] Settings UI: provider radio + per-provider model defaults + model-docs hyperlinks
- [x] Per-provider API keys in the Keychain (`api_key_anthropic`, `api_key_openai`)

### Milestone 5 — Media + MAS 8 (3–4 weeks) — **in progress** (`feat/milestone-5-media-mas8`)

**Proposed design decisions (confirm before building each part):**

1. **Audio transcription is local** — `faster-whisper` (CTranslate2 backend; no PyTorch), default model `small`, downloaded to the app-data dir on first use with progress reported through the source row. Audio never leaves the machine, consistent with §"Security & data".
2. **Video = audio path + ffmpeg** — extract the audio track with ffmpeg, then reuse the audio transcriber. ffmpeg comes from the `imageio-ffmpeg` wheel (ships a static binary — no Homebrew/system install needed, and PyInstaller picks it up as a normal package data file).
3. **Images are the one exception to "text only to the LLM"** — image bytes are sent to the *user's already-configured provider* (Claude / GPT-4o multimodal message) for OCR + description; only the returned text enters the pipeline. The security rule is amended to: "audio/video are processed locally; images may be sent to the configured provider's vision endpoint; raw media is never sent anywhere else."
4. **Status flow** — media uploads go `UPLOADED → TRANSCRIBING → EXTRACTED | ERROR` (the `PENDING` parking state disappears for supported media types). Processing auto-starts on upload as a FastAPI `BackgroundTask`, exactly like text extraction, and writes the same `extracted/{source_id}.txt` sidecar so the pipeline needs no changes.

**Checklist:**

- [ ] Author `knowledge/versions/mas-8.md` with all §7.3 H2 sections (real prose, not a stub); flip `mas-8` to Enabled in §7.2 and in the New Project modal
- [ ] `backend/extractors/audio.py` (faster-whisper), `video.py` (ffmpeg → audio → transcribe), `image.py` (provider vision via `llm_client.py` — still the only file importing provider SDKs)
- [ ] Add `TRANSCRIBING` to the §8 state machine and source-status API; update the §8 file-type table (`PENDING`/"No (Milestone 5)" rows become auto-processed)
- [ ] Frontend: media source rows show a TRANSCRIBING state with progress; transcription errors surface in the row like extraction errors
- [ ] Tests: unit tests per extractor with tiny fixture files; transcriber and vision calls mocked (no model download, no network in tests)
- [ ] Packaging: bundle ffmpeg + handle the Whisper model cache path in the PyInstaller build; rebuild and smoke-test the DMG

### Milestone 6 — Branding clone (2–3 weeks)

- [ ] `BrandingProfile` extraction + storage; renderer applies fonts/logo/table XML (best-effort)

### Milestone 7 — Ollama (1–2 weeks)

- [ ] `OllamaProvider` in `LLMClient`; model discovery endpoint + Settings UI

### Milestone 8 — Windows + polish (2–3 weeks)

- [ ] Windows electron-builder + PyInstaller; onboarding flow, accessibility pass, optional code signing

---

## 19. Risk Mitigations (Built-In)

| Risk | Mitigation in this spec |
|------|-------------------------|
| MVP architecture becomes a dead end | Same backend/API/UI in browser and Electron; only key storage + dialogs swap (§13) |
| Context overflow | Summarization at 12k chars; chronological source ordering |
| LLM JSON drift | Tool-use JSON + Pydantic validation; one "fix JSON" retry |
| Key leakage | Keychain (MVP) → safeStorage (M3); never in DB/logs; masked in UI |
| Large uploads | Stream to disk; 500 MB cap |
| Localhost backend exposed | Bind `127.0.0.1` only |
| Redundant extraction | Sidecar cache in `extracted/`; Stage 1 reads cache |
| Single-DB → portable-DB migration | All rows keyed by `project_id` from day one (§9.1) |
| Port conflict (Electron) | Dynamic port + health gate (M3) |
| Knowledge files thin at launch | Stubs unblock build; authoring is a tracked parallel task (§7.3) |

---

## 20. Day-0 Artifact Checklist

1. `docs/implementation-spec.md` (this file)
2. `backend/templates/brd_default_structure.json` (§7.1)
3. `knowledge/versions/maximo-76.md` (stub now, author per §7.3)
4. `knowledge/versions/mas-9.md` (stub now, author per §7.3)
5. `backend/prompts/*.txt` (§12.3–12.5)
6. `backend/models/pipeline.py` (§9.2)

---

## 21. Document Relationship

| Document | Role |
|----------|------|
| `docs/blueprint.md` | Product vision and constraints (reference only) |
| `docs/implementation-spec.md` | **Authoritative build specification** — use this to implement |

---

## 22. Summary

| Question | Answer |
|----------|--------|
| Is anything working now? | Yes — Milestones 0–3 complete: a double-click macOS desktop app (DMG) that produces a real BRD from real documents, with cancel mid-run, branded templates, timestamp overrides, and structured error handling — no terminal, no Python install |
| What's next? | Milestone 5 (in progress): media processing (audio/video/image) + MAS 8 knowledge — see §18 for the design decisions and checklist. (Windows packaging and native dialogs are tracked for Milestone 8.) |
| Did the MVP lock us in? | No — backend, API, schema, and UI carried into Electron **unchanged**; the desktop shell is a thin same-origin wrapper that only spawns and health-gates the backend |
| What was deferred, and where did it go? | Every deferred item has a named milestone in §3.2 / §18; safeStorage and the per-project DB split were consciously declined/deferred (kept `keyring` and a single `app.db`) — nothing from the blueprint was dropped |
| What's still content work? | Full Maximo knowledge files (structure defined in §7.3; prose must be authored before real client use) |
