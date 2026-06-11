# MaximoBRD — Self-Contained Implementation Specification

This document is everything needed to implement the project without referring back to `docs/plan.md` or `docs/blueprint.md`. It resolves ambiguities, defines schemas and API contracts, specifies prompts, and includes a phased build order with acceptance criteria.

**Status:** Ready for Phase 1 implementation  
**Platform:** macOS MVP (Windows in Phase 5)  
**Stack:** Electron + React + Vite + Tailwind + Zustand + Python FastAPI + SQLite

---

## 1. Product Goal

A local-first desktop app for IBM Maximo consultants that:

1. Creates a project (client, name, date, Maximo version, folder location).
2. Accepts requirement artifacts (documents now; audio/video/images later).
3. Runs a 3-stage pipeline (extract → analyze → generate/render).
4. Exports a DRAFT-watermarked DOCX BRD with traceable requirement IDs.

---

## 2. Locked Decisions

| Topic | Decision |
|-------|----------|
| AI providers (Phase 1) | Anthropic Claude + OpenAI |
| API keys | Electron `safeStorage` only — never in DB, logs, or `.env` |
| Project data | User-chosen folder per project + portable `project.db` |
| Global data | `app.db` in OS app data (project index + non-secret settings) |
| BRD structure | Branded DOCX → extract heading hierarchy; else `brd_default_structure.json` |
| BRD styling | Named Word styles only in Phase 1; visual branding clone → Phase 3 |
| Traceability (MVP) | Document-level (`source_ref` = filename) |
| Progress | SSE only — no polling |
| Agents | Sequential only — no parallel agent execution |
| Context overflow | Per-source summarization when `char_count > TOKEN_THRESHOLD` |
| Text files (Phase 1) | PDF, DOCX, TXT, MD, XLSX, XLS — extracted on upload |
| Media files (Phase 1) | Accepted and stored; status `PENDING`; skipped in pipeline |
| Maximo versions (Phase 1) | 7.6.0.x, 7.6.1.x, MAS 9.x enabled; MAS 8.x disabled ("Coming soon") |
| Distribution | Internal use; DMG build; no notarization in Phase 1 |

---

## 3. Architecture

```
Electron Main
  ├── spawns uvicorn (dynamic port via env MAXIMOBRD_PORT)
  ├── safeStorage for API keys
  └── IPC preload bridge

Electron Renderer (React)
  └── Zustand stores → IPC → localhost:PORT

FastAPI Backend
  ├── routes/       REST + SSE
  ├── services/     LLMClient, DocxRenderer, StructureExtractor
  ├── agents/       extractor, summarizer, analyzer, generator (sequential)
  ├── processors/   per file-type text extraction
  ├── models/       Pydantic inter-stage contracts
  └── db/           SQLAlchemy async + Alembic

Project Folder (user path)
  ├── project.db
  ├── sources/          raw uploads
  ├── extracted/        {source_id}.txt sidecars
  ├── branding/         optional branded reference DOCX
  └── output/           {run_id}.docx

App Bundle / Repo
  ├── knowledge/versions/*.md
  └── templates/brd_default_structure.json
```

### Process lifecycle

1. `main.js` finds free TCP port → sets `MAXIMOBRD_PORT` → spawns `uvicorn backend.main:app`.
2. Poll `GET /health` every 500ms, max 30s, before showing main window.
3. On quit: SIGTERM child process; wait 5s; SIGKILL if needed.

### Dev vs production backend path

- **Dev:** `uvicorn` runs from repo `backend/` with system Python venv.
- **Prod:** PyInstaller binary bundled in Electron `resources/backend/`.

---

## 4. Repository Layout

```
maximobrd/
├── electron/
│   ├── main.js
│   ├── preload.js
│   └── package.json
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   ├── pages/
│   │   │   ├── ProjectList.jsx
│   │   │   ├── ProjectDetail.jsx
│   │   │   ├── Generate.jsx
│   │   │   └── Settings.jsx
│   │   └── store/
│   │       ├── projectStore.js
│   │       ├── settingsStore.js
│   │       └── pipelineStore.js
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.js
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── routes/
│   │   ├── projects.py
│   │   ├── pipeline.py
│   │   └── settings.py
│   ├── services/
│   │   ├── llm_client.py
│   │   ├── docx_renderer.py
│   │   └── structure_extractor.py
│   ├── agents/
│   │   ├── extractor.py
│   │   ├── summarizer.py
│   │   ├── analyzer.py
│   │   └── generator.py
│   ├── processors/
│   │   ├── pdf.py, docx.py, xlsx.py, plaintext.py
│   │   └── (audio.py, video.py, image.py — Phase 2)
│   ├── models/
│   │   ├── project.py, pipeline.py, settings.py
│   ├── db/
│   │   ├── database.py
│   │   └── migrations/
│   ├── prompts/
│   │   ├── summarizer.txt
│   │   ├── analyzer_system.txt
│   │   ├── analyzer_user.txt
│   │   ├── generator_system.txt
│   │   └── generator_user.txt
│   ├── templates/
│   │   └── brd_default_structure.json
│   └── requirements.txt
├── knowledge/versions/
│   ├── maximo-76.md
│   ├── mas-8.md          (Phase 2)
│   └── mas-9.md
├── docs/
│   ├── plan.md
│   └── implementation-spec.md   (this document)
└── package.json                   (workspace root + electron-builder)
```

---

## 5. Prerequisites (Create Before Coding)

### 5.1 `templates/brd_default_structure.json`

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

### 5.2 Maximo version mapping

| UI label | `maximo_version` key | Knowledge file | Phase 1 |
|----------|----------------------|----------------|---------|
| Maximo 7.6.0.x | `maximo-760` | `maximo-76.md` | Enabled |
| Maximo 7.6.1.x | `maximo-761` | `maximo-76.md` | Enabled |
| MAS 8.x | `mas-8` | `mas-8.md` | Disabled |
| MAS 9.x | `mas-9` | `mas-9.md` | Enabled |

### 5.3 Knowledge file minimum content (each file)

Each `knowledge/versions/*.md` must include these H2 sections:

- Platform Overview
- Deployment Model
- Customization Mechanisms (MBO, automation scripts, etc.)
- Integration Patterns
- Native vs Custom — decision guidance
- Common Module Capabilities (WO, ASSET, INV, PURCH, PM, SR)
- Upgrade / Migration Considerations
- Known Platform Limitations

Content is injected verbatim into analyzer/generator system prompts. Do not hardcode version facts in Python.

### 5.4 Default AI models

| Provider | Default `model_id` | Settings placeholder |
|----------|-------------------|----------------------|
| `anthropic` | `claude-sonnet-4-6` | Claude Sonnet 4.6 |
| `openai` | `gpt-4o` | GPT-4o |

### 5.5 Maximo module codes (for `BRD-{MODULE}-{NNN}`)

Allowed `MODULE` values (3–8 uppercase letters):

```
WO, ASSET, INV, PURCH, PM, SR, LABOR, CAL, BUDGET, METER, ROUTES, SLA, LOC, PERSON, COMP, SAFETY, CONTRACT, RFQ, REORDER, GL, ESCALATION, KPI, MOBILE, INTEGRATION, GENERAL
```

ID assignment (deterministic, post-LLM):

- Group requirements by `module`.
- Sort by `sort_order` from LLM (fallback: original list order).
- Assign `BRD-{MODULE}-001`, `BRD-{MODULE}-002`, … per module.

---

## 6. Source Processing State Machine

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
              (audio/video/image Phase 1)
                    ┌──────▼──────┐
                    │   PENDING   │  "Processing available in Phase 2"
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
| mp3, wav, m4a, ogg | `audio` | PENDING | No (Phase 2) |
| mp4, mov, webm | `video` | PENDING | No (Phase 2) |
| png, jpg, jpeg, webp | `image` | PENDING | No (Phase 2) |
| other | `unknown` | ERROR | No — error message set |

---

## 7. Data Models

### 7.1 Database — Global `app.db`

**`projects_index`**

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | Same as project.id |
| client_name | TEXT | |
| project_name | TEXT | |
| folder_path | TEXT UNIQUE | Absolute path |
| maximo_version | TEXT | |
| created_at | DATETIME | |
| updated_at | DATETIME | |

**`provider_settings`**

| Column | Type | Notes |
|--------|------|-------|
| id | INT PK | Singleton row `id=1` |
| provider | TEXT | `anthropic` \| `openai` |
| model_id | TEXT | |
| api_key_storage_key | TEXT | Key name in safeStorage, e.g. `maximobrd.api_key` |
| updated_at | DATETIME | |

### 7.2 Database — Per-project `project.db`

**`projects`** (singleton metadata row)

| Column | Type |
|--------|------|
| id | UUID PK |
| client_name | TEXT |
| project_name | TEXT |
| project_date | DATE |
| maximo_version | TEXT |
| folder_path | TEXT |
| branded_docx_path | TEXT NULL |
| created_at | DATETIME |

**`sources`**

| Column | Type |
|--------|------|
| id | UUID PK |
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
| status | TEXT |
| started_at | DATETIME |
| completed_at | DATETIME NULL |
| output_path | TEXT NULL |
| error_message | TEXT NULL |
| sources_used_count | INTEGER |
| skipped_sources_count | INTEGER |

### 7.3 Pydantic — Pipeline contracts (`backend/models/pipeline.py`)

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

class AnalysisResult(BaseModel):
    requirements: list[Requirement]
    modules_referenced: list[str]
    analysis_notes: str | None = None

class NarrativeSection(BaseModel):
    section_id: str                # matches brd_default_structure id
    title: str
    body: str                      # plain text, paragraphs separated by \n\n

class BRDDocument(BaseModel):
    project_metadata: dict         # client, project, date, maximo_version
    structure: list[dict]          # ordered sections from template or branded DOCX
    narratives: list[NarrativeSection]
    requirements: list[Requirement]
    appendix_sources: list[str]    # unique filenames used
```

### 7.4 Requirement table columns (DOCX)

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

## 8. API Contract

Base URL: `http://127.0.0.1:{PORT}`  
All errors: `{ "error": { "code": "STRING", "message": "Human readable" } }`  
Never return Python stack traces to the renderer.

### 8.1 Health

`GET /health` → `200`

```json
{ "status": "ok", "version": "0.1.0" }
```

### 8.2 Projects

`POST /projects`

```json
{
  "client_name": "Acme Corp",
  "project_name": "EAM Upgrade",
  "project_date": "2026-06-01",
  "maximo_version": "mas-9",
  "folder_path": "/Users/consultant/Projects/acme-eam"
}
```

Response `201`:

```json
{
  "id": "uuid",
  "client_name": "Acme Corp",
  "project_name": "EAM Upgrade",
  "project_date": "2026-06-01",
  "maximo_version": "mas-9",
  "folder_path": "/Users/consultant/Projects/acme-eam",
  "branded_docx_path": null,
  "created_at": "2026-06-07T10:00:00Z"
}
```

Side effects: create folder structure, `project.db`, register in `app.db`.

`GET /projects` → `200` list of project summaries from `app.db`.

`GET /projects/{id}` → `200` full project + source count + latest run.

`DELETE /projects/{id}` → `204` (removes from index only; does not delete folder).

`PUT /projects/{id}/branding` — multipart upload of branded DOCX → saves to `branding/reference.docx`, updates `branded_docx_path`.

### 8.3 Sources

`POST /projects/{id}/sources/upload`

- **Content-Type:** `multipart/form-data`
- **Fields:** `file` (binary stream), optional `source_timestamp` (ISO string), optional `user_timestamp_override` (ISO string)
- **Filename collision:** append `_{n}` before extension (`workshop.pdf` → `workshop_1.pdf`)
- **Max size:** 500 MB (configurable `MAX_UPLOAD_BYTES`)
- Streams to disk via `aiofiles`; never buffers full file in RAM

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

Extraction runs as FastAPI `BackgroundTask` immediately after upload.

`GET /projects/{id}/sources` → `200` array of source objects.

`DELETE /projects/{id}/sources/{source_id}` → `204` (deletes file + sidecar + DB row).

`PATCH /projects/{id}/sources/{source_id}`

```json
{ "user_timestamp_override": "2026-05-10T14:00:00Z" }
```

### 8.4 Settings

API keys never pass through FastAPI in production storage. Flow:

1. Renderer calls `storage:set` via IPC with key `maximobrd.api_key`.
2. Renderer calls `POST /settings/provider` with provider + model only.
3. On LLM call, main process injects key into backend via `X-API-Key` header on internal requests only (localhost).

`GET /settings/provider` → `200`

```json
{
  "provider": "anthropic",
  "model_id": "claude-sonnet-4-6",
  "configured": true
}
```

`POST /settings/provider`

```json
{ "provider": "anthropic", "model_id": "claude-sonnet-4-6" }
```

`POST /settings/provider/test` — backend reads key from request header `X-API-Key` (supplied by IPC layer), makes minimal completion ("Reply OK"), returns:

```json
{ "success": true, "latency_ms": 842 }
```

### 8.5 Pipeline

`POST /projects/{id}/generate`

- Validates: provider configured, ≥1 `EXTRACTED` source.
- Creates `pipeline_runs` row with `status=RUNNING`.
- Starts background pipeline task.
- Returns `202`:

```json
{ "run_id": "uuid", "status": "RUNNING" }
```

`GET /pipeline/{run_id}` → run metadata.

`GET /pipeline/{run_id}/stream` — SSE (see §9).

`POST /pipeline/{run_id}/cancel` → `200` — sets cancel flag; pipeline checks between stages.

`GET /pipeline/{run_id}/download` → `application/vnd.openxmlformats-officedocument.wordprocessingml.document` stream.

`GET /projects/{id}/runs` → list of past pipeline runs.

---

## 9. SSE Event Specification

**Upload progress:** for MVP, upload progress is an IPC-level byte callback from the renderer during fetch; refresh source status via `GET /sources` after upload completes.

**Pipeline stream** `GET /pipeline/{run_id}/stream`

```
Content-Type: text/event-stream
```

Event format:

```
event: progress
data: {"stage":"extraction","step":null,"message":"Processing workshop.pdf","percent":12,"run_id":"..."}

event: progress
data: {"stage":"analysis","step":"summarizing","message":"Summarizing requirements.xlsx","percent":42,"run_id":"..."}

event: done
data: {"stage":"done","output_path":"/path/to/output/uuid.docx","percent":100,"run_id":"..."}

event: error
data: {"stage":"failed","message":"Analysis validation failed","percent":0,"run_id":"..."}
```

| stage | percent range |
|-------|---------------|
| extraction | 0–30 |
| analysis / summarizing | 30–55 |
| analysis / extracting | 55–75 |
| generation | 75–90 |
| rendering | 90–100 |
| done | 100 |
| failed | — |

Stream closes after `done` or `error`. Frontend reconnect: not required for MVP.

---

## 10. IPC Contract (`electron/preload.js`)

| Channel | Direction | Payload | Returns |
|---------|-----------|---------|---------|
| `api:call` | renderer → main | `{ method, path, body?, headers? }` | `{ status, data }` |
| `api:stream` | renderer → main | `{ path }` | emits `api:stream:event` |
| `storage:set` | renderer → main | `{ key, value }` | `boolean` |
| `storage:get` | renderer → main | `{ key }` | `string \| null` |
| `dialog:openFiles` | renderer → main | `{ filters?, multi? }` | `string[]` |
| `dialog:openFolder` | renderer → main | `{}` | `string \| null` |
| `dialog:saveFile` | renderer → main | `{ defaultPath, filters? }` | `string \| null` |

`api:call` automatically attaches `X-API-Key` from safeStorage when path starts with `/settings/` test or any `/pipeline/` generate path needs it — implement: attach key header on all backend calls except `GET /health` and `GET /projects`.

---

## 11. Pipeline Implementation Detail

### 11.1 Pre-flight

1. Load `project` from `project.db`.
2. Load knowledge: `VERSION_MAP[maximo_version]` → read `.md` file.
3. Load BRD structure:
   - If `branded_docx_path` set → `StructureExtractor.extract_headings()` → `list[str]`.
   - Else → load `brd_default_structure.json` → `sections[].title`.
4. Load sources where `processing_status == EXTRACTED`, ordered by effective timestamp (`user_timestamp_override ?? source_timestamp`).
5. Load provider config + API key (from IPC header).

### 11.2 Stage 1 — Extractor (`agents/extractor.py`)

For each eligible source:

1. Read `extracted/{source_id}.txt` if exists and non-empty.
2. Else dispatch processor, write sidecar, update DB.
3. Build `ExtractedSource`.
4. Emit SSE per file.

### 11.3 Stage 2a — Summarizer (`agents/summarizer.py`)

`TOKEN_THRESHOLD` = env var, default `12000` characters.

**Prompt template** (`prompts/summarizer.txt`):

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

### 11.4 Stage 2b — Analyzer (`agents/analyzer.py`)

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

`complete_json()` schema = `AnalysisResult` with `RequirementDraft` items (no `id` field). Post-process: assign `BRD-{MODULE}-{NNN}` IDs.

### 11.5 Stage 3a — Generator (`agents/generator.py`)

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

Validate output as `BRDDocument`.

### 11.6 Stage 3b — DocxRenderer (`services/docx_renderer.py`)

1. Create blank Document.
2. Add DRAFT watermark via header XML injection (not text box).
3. For each structure section in order:
   - Heading 1/2/3 based on level.
   - If section id = `requirements`: group by module, Heading 2 per module, Table per module.
   - If narrative section: render paragraphs as Normal.
4. Appendix: bullet list of source filenames.
5. Save to `{folder}/output/{run_id}.docx`.

### 11.7 LLMClient (`services/llm_client.py`)

```python
class LLMClient:
    async def complete(self, messages: list[dict], max_tokens: int = 4096) -> str: ...
    async def complete_json(self, messages: list[dict], schema: type[BaseModel], max_tokens: int = 8192) -> dict: ...
```

- 3 retries, exponential backoff from 2s.
- Anthropic: `messages.create`; JSON via tool use or structured output.
- OpenAI: `response_format={"type":"json_object"}`; prepend schema in system message.
- Only file importing `anthropic` / `openai` SDKs.

---

## 12. UI Specification

### 12.1 Navigation

```
/                  → ProjectList
/projects/:id      → ProjectDetail
/projects/:id/generate → Generate (pipeline progress)
/settings          → Settings
```

No HTML `<form>` tags. React `onClick` / `onChange` only. No localStorage/sessionStorage.

### 12.2 ProjectList

- Table: client, project name, date, Maximo version, created.
- "New Project" opens modal:
  - client_name (required)
  - project_name (required)
  - project_date (date picker, default today)
  - maximo_version (select; mas-8 disabled with tooltip)
  - folder (dialog:openFolder; required)
- Empty state: "Create your first project"
- First-run gate: if provider not configured, banner linking to Settings.

### 12.3 ProjectDetail

Sections:

1. **Project metadata** (read-only header).
2. **Branded template** — upload DOCX; show extracted headings preview after upload.
3. **Sources** — drag-drop zone + browse button:
   - Columns: filename, size, effective date, status badge, actions (delete, edit date).
   - Status badges: Extracting, Ready (EXTRACTED), Pending, Error (with tooltip).
4. **Generate** button — disabled unless ≥1 EXTRACTED source AND provider configured.
5. **Run history** — table of past runs with status, date, download button.

### 12.4 Generate page

- Progress bar (0–100) driven by SSE.
- Stage checklist: Extraction → Analysis → Generation → Rendering.
- Live message log (last 5 messages).
- Cancel button → `POST /cancel`.
- On `done`: "Save BRD" → `dialog:saveFile` copies output to user path.
- On `error`: show message + "Return to project" + "Retry".

### 12.5 Settings

- Provider radio: Claude | OpenAI
- Model text input with default suggestion
- API key password field → `storage:set` on save
- Test Connection button
- Save button

---

## 13. Configuration (`backend/config.py`)

| Variable | Default | Purpose |
|----------|---------|---------|
| `TOKEN_THRESHOLD` | `12000` | Chars before summarization |
| `MAX_UPLOAD_BYTES` | `524288000` | 500 MB |
| `LLM_MAX_TOKENS_SUMMARIZE` | `4096` | |
| `LLM_MAX_TOKENS_ANALYZE` | `8192` | |
| `LLM_MAX_TOKENS_GENERATE` | `8192` | |
| `APP_DATA_DIR` | OS-specific | `app.db` location |
| `MAXIMOBRD_PORT` | dynamic | Set by Electron |

---

## 14. Local Development Setup

### 14.1 Prerequisites

- Node 20+, Python 3.11+, npm

### 14.2 First-time setup

```bash
# Root
npm install

# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

### 14.3 Run (three terminals)

```bash
# Terminal 1 — Backend
cd backend && source .venv/bin/activate
MAXIMOBRD_PORT=8765 uvicorn main:app --reload --port 8765

# Terminal 2 — Frontend
cd frontend && npm run dev

# Terminal 3 — Electron
cd electron && MAXIMOBRD_PORT=8765 BACKEND_DEV=1 npm run start
```

`BACKEND_DEV=1` tells Electron not to spawn its own uvicorn (use existing dev server).

### 14.4 Root `package.json` scripts (target)

```json
{
  "scripts": {
    "dev:backend": "cd backend && uvicorn main:app --reload --port 8765",
    "dev:frontend": "cd frontend && npm run dev",
    "dev:electron": "cd electron && MAXIMOBRD_PORT=8765 BACKEND_DEV=1 npm run start",
    "build:mac": "npm run build:backend && npm run build:frontend && electron-builder --mac"
  }
}
```

---

## 15. Testing Strategy

### 15.1 Unit tests (pytest)

| Module | Tests |
|--------|-------|
| `processors/pdf.py` | sample PDF → non-empty text |
| `processors/docx.py` | paragraphs + tables |
| `structure_extractor.py` | heading hierarchy order |
| `docx_renderer.py` | tables exist, DRAFT header present, named styles only |
| ID assignment | `BRD-WO-001` sequencing |
| `llm_client.py` | retry logic (mocked) |

### 15.2 Integration tests

- Create project → upload TXT → wait EXTRACTED → generate (mock LLM) → DOCX file exists.
- Malformed PDF → ERROR status + message.

### 15.3 Manual E2E (Phase 1 exit criteria)

1. Real Claude or OpenAI key configured.
2. Upload 1 PDF + 1 DOCX.
3. Generate BRD.
4. Open DOCX in Word: headings correct, requirement tables present, DRAFT watermark visible, IDs formatted `BRD-*-NNN`.

---

## 16. Phased Build Plan

### Phase 0 — Day 1 Spike (2 days)

**Goal:** Prove Electron → IPC → FastAPI round trip.

- [ ] Scaffold all three packages
- [ ] `/health` displayed in React
- [ ] safeStorage round-trip test
- [ ] Create prerequisite files: `brd_default_structure.json`, stub `maximo-76.md` + `mas-9.md` (expand content in parallel)

**Done when:** Window opens, health check green, IPC test button works.

---

### Phase 1 — MVP (6–8 weeks)

#### Week 1 — Scaffold + DB

- [ ] IPC channels per §10
- [ ] `app.db` + `project.db` engines, Alembic migrations
- [ ] Project CRUD routes + ProjectList/Detail UI (no upload yet)

#### Week 2 — Upload + Extraction

- [ ] Streaming upload endpoint
- [ ] All four text processors
- [ ] Background extraction + status transitions
- [ ] Source list UI with badges

#### Week 3 — Settings + LLMClient

- [ ] Provider settings routes
- [ ] `LLMClient` with Claude + OpenAI
- [ ] Settings page + test connection
- [ ] API key via safeStorage + header injection

#### Week 4–5 — Pipeline

- [ ] `PipelineRun` model + generate/cancel/stream routes
- [ ] All four agents + prompt files
- [ ] Structure extractor + branded DOCX upload
- [ ] Generate page with SSE progress

#### Week 6 — DOCX + Export

- [ ] `DocxRenderer` complete per §7.4
- [ ] Download + save dialog flow
- [ ] Run history on ProjectDetail

#### Week 7 — Hardening

- [ ] Error boundaries (React)
- [ ] Structured API errors
- [ ] Cancel pipeline
- [ ] Filename collision + corrupt file handling

#### Week 8 — Packaging

- [ ] PyInstaller spec (no Torch)
- [ ] electron-builder DMG
- [ ] Smoke test on clean Mac

**Phase 1 Definition of Done:**

- [ ] All §15.3 manual E2E passes
- [ ] Pending audio/video files upload without breaking generate
- [ ] No API keys in logs or database
- [ ] DMG installs and runs without dev tools

---

### Phase 2 — Media + MAS 8 (3–4 weeks)

- [ ] Author `mas-8.md`
- [ ] Enable `mas-8` in UI
- [ ] `audio.py`, `video.py`, `image.py` processors
- [ ] Whisper + ffmpeg bundling
- [ ] `PENDING → TRANSCRIBING → EXTRACTED` flow
- [ ] Vision API for images (text only sent to LLM)

---

### Phase 3 — Branding Clone (2–3 weeks)

- [ ] `BrandingProfile` extraction + storage
- [ ] Renderer applies fonts/logo/table XML (best-effort)

---

### Phase 4 — Ollama (1–2 weeks)

- [ ] `OllamaProvider` in `LLMClient`
- [ ] Model discovery endpoint + Settings UI

---

### Phase 5 — Windows + Polish (2–3 weeks)

- [ ] Windows electron-builder + PyInstaller
- [ ] Onboarding flow, accessibility pass
- [ ] Optional code signing

---

## 17. Risk Mitigations (Built-In)

| Risk | Mitigation in this spec |
|------|-------------------------|
| Context overflow | Summarization at 12k chars; chronological source ordering |
| LLM JSON drift | Pydantic validation; retry once with "fix JSON" prompt on failure |
| Port conflict | Dynamic port + health gate |
| Large uploads | Stream to disk; 500 MB cap |
| Key leakage | safeStorage only; header injection; no logging |
| READY vs EXTRACTED confusion | Single state machine in §6 |
| Redundant extraction | Sidecar cache in `extracted/`; Stage 1 reads cache |

---

## 18. Day-0 Artifact Checklist

Create these files before or during Phase 0:

1. `docs/implementation-spec.md` (this file)
2. `backend/templates/brd_default_structure.json` (§5.1)
3. `knowledge/versions/maximo-76.md` (author content per §5.3)
4. `knowledge/versions/mas-9.md` (author content per §5.3)
5. `backend/prompts/*.txt` (§11.3–11.5 templates)
6. `backend/models/pipeline.py` (§7.3)

---

## 19. Document Relationship

| Document | Role |
|----------|------|
| `docs/blueprint.md` | Product vision and constraints (reference only) |
| `docs/plan.md` | Architectural rationale and stakeholder decisions (reference only) |
| `docs/implementation-spec.md` | **Authoritative build specification** — use this to implement |

---

## 20. Summary

| Question | Answer |
|----------|--------|
| Is this enough to implement? | **Yes**, for Phase 1 through packaging |
| What's still judgment calls during build? | Visual polish, exact Tailwind styling, PyInstaller edge cases |
| What's still content work? | Full Maximo knowledge files (structure defined, prose must be authored) |
