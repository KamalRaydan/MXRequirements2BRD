# Plan: Maximo Test Case Generation

> **Status:** Deferred. Saved for a future milestone — revisit after the
> original project milestones (M5 media/MAS 8, M6 branding clone) are complete.
> Proposed as **Milestone 7 — Test Case Generation**.

## Context

MaximoBRD today turns source documents into a BRD (DOCX) via a sequential agent
pipeline (extractor → summarizer → analyzer → generator → docx renderer). The
next capability the consultant needs is **Test Cases** — an Excel sheet, one
worksheet, each row exercising a requirement — so that (a) every test traces back
to a specific BRD requirement, and (b) running the tests proves the Maximo
configuration actually works.

Three real-world situations must be supported:
1. **Tests only** — consultant already has a finished BRD (made elsewhere) and
   just wants test cases from it.
2. **BRD then tests** — generate the BRD in-app first, then tests from it.
3. **Custom structure** — consultant already has an Excel test-case template
   whose columns must be reused instead of our default layout.

The clean mental model that unifies all three: **test generation needs two
inputs — a Requirements Set and a Test Structure — each sourced two ways.**

| Input | Option A | Option B |
|-------|----------|----------|
| Requirements Set | Reuse requirements saved from an in-app BRD run (Scenario 2) | Ingest an uploaded external BRD docx (Scenario 1) |
| Test Structure | Built-in default columns | Columns read from an uploaded Excel template (Scenario 3) |

### Decisions locked with the user
- **Granularity:** one requirement → **many** test cases allowed; every test row
  still carries its Requirement ID.
- **Default columns (the "middle" set):** `Test Case ID | Requirement ID | BRD
  Reference | Module | Test Scenario | Preconditions | Test Steps | Expected
  Result | Status | Notes`. A custom uploaded template overrides this.
- **Traceability:** the Requirement ID is not enough on its own — each test row
  also carries a human-readable **BRD Reference** (e.g. `Business Requirements ›
  Work Order Management › BRD-WO-001` for in-app BRDs, or the nearest
  section/heading the LLM finds in an external BRD). Page numbers are *not* used
  (DOCX has no reliable pagination); section/heading + ID is the locator.
- **Scenario 2 UX:** two steps. The BRD runs as today and now **saves its
  requirements**; when it finishes, a "Generate Test Cases" button reuses that
  saved snapshot (no re-analysis, no extra LLM cost).
- **No new dependencies.** `openpyxl` is already used in
  `backend/processors/xlsx.py`.

This is a new milestone (proposed **Milestone 7 — Test Case Generation**) and
should be recorded in `docs/implementation-spec.md`.

---

## Architecture: reuse the existing run machinery

A test run is just another `PipelineRun`, distinguished by a new `kind` column
(`"BRD"` default vs `"TESTS"`). This reuses the entire ProgressBus / SSE /
cancel / stream / status plumbing untouched. Only the download route and a few
Pydantic responses need to stop assuming "docx".

```
Scenario 2 (BRD → tests):
  run_pipeline (existing)  ── now also writes ──▶ output/requirements_{run_id}.json
        │ done
        ▼
  [Generate Test Cases]  POST /generate-tests {requirements_source:"brd_run", source_run_id}
        │
        ▼  run_test_pipeline(kind="TESTS")
  load snapshot → test_generator (LLM) → assign TC ids → xlsx_renderer → output/{run_id}.xlsx

Scenario 1 (tests from uploaded BRD):
  POST /brd-files (multipart docx)  → stored in {folder}/brd_input/
        │
        ▼  POST /generate-tests {requirements_source:"uploaded_brd", brd_filename}
  run_test_pipeline → brd_ingest (heading-annotate + LLM extract w/ BRD Reference)
        → test_generator → xlsx_renderer

Scenario 3 (custom columns): orthogonal — PUT /test-template stores an xlsx;
  its header row becomes the column set for either scenario above.
```

---

## Backend changes

### 1. Data model (`backend/db/models.py` + `backend/db/database.py`)
- `PipelineRun`: add `kind: str` (default `"BRD"`) and `requirements_path: str |
  None` (sidecar JSON written by BRD runs and read by test runs).
- `Project`: add `test_template_path: str | None` (uploaded custom Excel
  template, analogous to existing `branded_docx_path`).
- **Migration:** there is no Alembic (`database.py` only calls `create_all`,
  which will not ALTER existing tables). Add a tiny idempotent guard in
  `init_db()` that, after `create_all`, runs `ALTER TABLE ... ADD COLUMN` for
  each new column when `PRAGMA table_info` shows it missing. Keep it ~10 lines,
  beginner-readable.

### 2. Pydantic schemas (`backend/models/pipeline.py`)
- Add optional `brd_reference: str | None` to `Requirement` (populated for
  in-app BRDs deterministically; filled by the LLM for ingested BRDs).
- New: `TestCaseDraft` (`requirement_id`, `brd_reference`, `module`,
  `scenario`, `preconditions`, `test_steps`, `expected_result`, `notes`,
  `sort_order`) and `TestCase` (adds `id = TC-{MODULE}-{NNN}`). `TestCaseSet`
  wraps `list[TestCaseDraft]` for the LLM call (mirrors `AnalysisDraft`).
- New: `IngestedRequirement` for external-BRD extraction (same shape as
  `Requirement` plus `brd_reference`; preserves any ID the LLM finds).

### 3. Persist requirements from BRD runs (`backend/agents/runner.py`)
In `run_pipeline`, after analysis, write the requirements list (with each
requirement's `brd_reference` derived as `Business Requirements › {module} ›
{id}`) to `output/requirements_{run_id}.json` and set
`run.requirements_path`. This is the snapshot Scenario 2 reuses. Small, additive
change — does not alter BRD output.

### 4. New agent — `backend/agents/test_generator.py`
- `generate_test_cases(llm, requirements, project_metadata, maximo_knowledge) ->
  list[TestCaseDraft]` then `assign_test_ids()` → `TC-{MODULE}-{NNN}`.
- `assign_test_ids()` mirrors `analyzer.assign_ids()` (group by module, sort by
  `sort_order`, number per module).
- Prompts `backend/prompts/test_generator_system.txt` + `_user.txt`. The system
  prompt **injects the Maximo version knowledge** so steps name real apps,
  fields and statuses (e.g. "In Work Order Tracking, create a WO and verify
  status = WAPPR") — this is what makes a passing test prove the config works.
  The user prompt passes the requirements JSON and instructs 1-to-many coverage
  (happy path + key negative/edge cases per requirement) while echoing each
  requirement's ID and BRD Reference verbatim into every generated row.

### 5. External BRD ingestion — `backend/services/brd_ingest.py`
- `ingest_brd(llm, docx_path, maximo_knowledge) -> list[Requirement]`.
- Walk the docx tracking the current Heading 1–3 path (reuse the heading-level
  logic from `services/structure_extractor.py:_heading_level`), producing
  **heading-annotated text** (insert `## {heading}` markers, and emit table rows
  as text). Feed that to the LLM via `complete_json` with `IngestedRequirement`,
  instructing it to (a) preserve any existing requirement IDs it sees, (b)
  otherwise derive easy-to-trace IDs, and (c) set `brd_reference` to the nearest
  heading. Assign IDs only where the LLM left them blank (reuse the
  `assign_ids` numbering helper, generalized).

### 6. Excel rendering — `backend/services/xlsx_renderer.py`
- `render_tests(test_cases, columns, output_path)` using `openpyxl`.
- One worksheet "Test Cases", styled bold/filled frozen header row, one row per
  test case, sensible column widths, wrapped text for steps; a Status
  data-validation dropdown (Pass/Fail/Blocked/Not Run) when a Status column is
  present. `columns` is the list of `{header, maps_to}` from the structure file
  or the uploaded template; any unmapped column renders empty.

### 7. Test structure files & custom-template reader
- `backend/templates/test_case_default_structure.json` — the middle column set,
  each entry `{ "id", "header", "maps_to", "width" }` where `maps_to` is a
  `TestCase` field name.
- `backend/services/xlsx_structure_extractor.py` —
  `extract_columns(xlsx_path) -> list[dict]`: read the header row of an uploaded
  template and map each header to a `TestCase` field via keyword matching (same
  pattern as `structure_extractor._CANONICAL_KEYWORDS`). Unrecognized headers
  are kept and rendered (left blank).

### 8. Test pipeline orchestrator (`backend/agents/runner.py`)
- `run_test_pipeline(run_id, project_id, api_key, model_id, provider,
  requirements_source, source_run_id=None, brd_filename=None)`:
  pre-flight (knowledge + LLM client) → obtain requirements (load snapshot OR
  `brd_ingest`) → load columns (default JSON or `xlsx_structure_extractor` on
  `project.test_template_path`) → `test_generator` → `xlsx_renderer` to
  `output/{run_id}.xlsx`. Same `_progress`/`_check_cancel`/ProgressBus events and
  the same DONE/FAILED/CANCELLED handling as `run_pipeline`.

### 9. Routes (`backend/routes/pipeline.py`, or a new `backend/routes/tests.py`)
- `POST /projects/{id}/generate-tests` (JSON): `{requirements_source:
  "brd_run"|"uploaded_brd", source_run_id?, brd_filename?}` → validates key +
  inputs, creates `PipelineRun(kind="TESTS")`, `background_tasks.add_task(
  run_test_pipeline, ...)`. Mirrors the existing `/generate` route.
- `POST /projects/{id}/brd-files` (multipart): store an uploaded external BRD
  docx under `{folder}/brd_input/`, return its filename. (Reuses the upload
  validation style from the sources route.)
- `PUT/GET/DELETE /projects/{id}/test-template` (multipart PUT): manage the
  custom Excel template + return a column preview (mirrors the branding routes).
- **Generalize `GET /pipeline/{run_id}/download`**: pick MIME + filename by the
  run's output extension (`.docx` → BRD, `.xlsx` → `Test Cases - {client} -
  {project}.xlsx`) instead of hardcoding DOCX. Update the "no completed BRD"
  message to be artifact-neutral.

---

## Frontend changes (React + Vite + Zustand)

- **`pipelineStore.js`**: add `startTests(projectId, payload)` → POST
  `/generate-tests`, then attach SSE exactly as `start()` does (the store is
  already generic over `run_id`). Download reuses `downloadUrl(runId)` (now
  serves xlsx). No new store needed.
- **`api.js`**: add `generateTests`, `uploadBrdFile`, `get/put/deleteTestTemplate`.
- **`Generate.jsx`**: on BRD `done`, show a **"Generate Test Cases"** button
  (Scenario 2) that calls `startTests` with `source_run_id = runId`.
- **New `GenerateTests.jsx`** (clone of `Generate.jsx`): same progress
  checklist (ingest → generating tests → rendering → done) + xlsx download.
- **`ProjectDetail.jsx`**: a "Test Cases" panel offering — requirements source
  (pick a completed BRD run, or upload an external BRD) and structure (default,
  or upload/replace a custom Excel template, shown like the branding control).
- Reuse `StatusBadge`, `ConfirmDialog`, existing SSE event handling.

---

## Tests (pytest, `backend/tests/`)
- `test_test_pipeline.py` — full flow with a **mocked LLM** returning a
  schema-valid `TestCaseSet`: create project → save a BRD run + requirements
  snapshot → POST `/generate-tests` → run reaches DONE → download returns a real
  `.xlsx` (PK zip). Mirror the existing `test_pipeline_integration.py` style.
- `test_assign_test_ids` — deterministic `TC-{MODULE}-{NNN}` grouping/ordering.
- `test_xlsx_structure_extractor` — header-row → field mapping (incl. an
  unrecognized column kept and blank-filled).
- `test_brd_ingest` (mocked LLM) — heading-annotated text is produced and
  `brd_reference` is carried through.
- Keep tests simple, behavior-focused, minimal mocking (per project rules).

---

## Critical files
- Modify: `backend/db/models.py`, `backend/db/database.py`,
  `backend/models/pipeline.py`, `backend/agents/runner.py`,
  `backend/routes/pipeline.py`, `frontend/src/store/pipelineStore.js`,
  `frontend/src/api.js`, `frontend/src/pages/Generate.jsx`,
  `frontend/src/pages/ProjectDetail.jsx`, `docs/implementation-spec.md`.
- New: `backend/agents/test_generator.py`, `backend/services/xlsx_renderer.py`,
  `backend/services/xlsx_structure_extractor.py`,
  `backend/services/brd_ingest.py`,
  `backend/templates/test_case_default_structure.json`,
  `backend/prompts/test_generator_system.txt`,
  `backend/prompts/test_generator_user.txt`,
  `frontend/src/pages/GenerateTests.jsx`, and the pytest files above.

## Reused patterns (don't reinvent)
- ID assignment: `backend/agents/analyzer.py:assign_ids` (model for `assign_test_ids`).
- Structure-from-document: `backend/services/structure_extractor.py` (model for
  `xlsx_structure_extractor` and the heading walk in `brd_ingest`).
- LLM JSON contract: `LLMClient.complete_json` + Pydantic schema (analyzer/generator).
- Run + SSE plumbing: `runner.run_pipeline`, `routes/pipeline.py`, `ProgressBus`.
- Excel reading: `backend/processors/xlsx.py` (openpyxl usage).

---

## Verification (end-to-end)
1. **Unit/integration:** `cd backend && python3.12 -m pytest` — new tests pass.
2. **Scenario 2 (BRD → tests):** start the app, run a BRD to completion, confirm
   `output/requirements_{run_id}.json` is written, click "Generate Test Cases",
   watch SSE progress, download the `.xlsx`. Open it: one worksheet, header row,
   multiple rows, every row's Requirement ID + BRD Reference matches a BRD
   requirement; steps cite real Maximo apps/statuses for the project's version.
3. **Scenario 1 (uploaded BRD):** in a project with no BRD run, upload an
   external BRD docx, generate tests, confirm requirement IDs/BRD References are
   extracted and traceable in the sheet.
4. **Scenario 3 (custom template):** upload a sample Excel template with custom
   headers, regenerate, confirm the output uses those columns (mapped fields
   filled, unmapped left blank).
5. **Regression:** a normal BRD run still produces the same DOCX and downloads
   correctly (download route generalization didn't break it).

## Build order (suggested)
1. Model + migration + requirements snapshot persistence (Scenario 2 foundation).
2. `test_generator` + `xlsx_renderer` + default structure + `run_test_pipeline`
   + `/generate-tests` + generalized download → Scenario 2 working end-to-end.
3. Frontend for Scenario 2.
4. `brd_ingest` + `/brd-files` → Scenario 1.
5. `xlsx_structure_extractor` + test-template routes/UI → Scenario 3.
6. Tests throughout; spec update last.
