# MaximoBRD

> Turn raw requirement documents into a polished, traceable Business Requirements Document (BRD) for IBM Maximo engagements — locally, on your own machine.

**Status:** Milestones 0–4 complete. Ships today as a double-click **macOS desktop app** (DMG) — no terminal, no Python install. The same app also runs in a browser for development.

---

## What it does

MaximoBRD is a local-first tool for IBM Maximo consultants. You:

1. **Create a project** — client, name, date, Maximo version, and where the files live.
2. **Upload requirement artifacts** — PDF, DOCX, TXT/MD, XLSX (audio/video/images are accepted but processed in a later release).
3. **Click Generate** — a 3-stage AI pipeline (extract → analyze → generate) reads your documents and drafts the BRD.
4. **Download a DOCX** — a DRAFT-watermarked Word document with traceable requirement IDs (`BRD-{MODULE}-{NNN}`) and source citations.

Everything runs on your machine. Your documents and API keys never leave it except for the **extracted text** sent to your chosen AI provider.

---

## How it works

```
┌─────────────────────────────┐
│  Desktop window (Electron)  │   ← macOS app; loads the local URL below
└──────────────┬──────────────┘
               │  loads http://127.0.0.1:<port>/
┌──────────────▼──────────────┐
│  React UI (Vite + Tailwind) │   ← also runs in a plain browser for dev
└──────────────┬──────────────┘
               │  fetch / Server-Sent Events
┌──────────────▼──────────────┐
│   FastAPI backend (Python)  │
│   ├─ routes/   REST + SSE   │
│   ├─ agents/   the pipeline │   extractor → summarizer → analyzer → generator
│   ├─ services/ LLM, DOCX    │
│   └─ db/       SQLite        │
└──────────────┬──────────────┘
               │
   ┌───────────┴───────────────┐
   │ OS keychain  → API keys   │   (macOS Keychain / Windows Credential Locker)
   │ app data dir → app.db     │
   │ project dir  → your files │
   └───────────────────────────┘
```

The desktop app is a thin shell: it picks a free port, starts the Python backend, waits for it to be healthy, then opens a window pointed at the backend's own URL. Because the backend already serves the UI, the browser and desktop versions share **identical** code.

---

## Tech stack

| Layer | Tools |
|-------|-------|
| Frontend | React, Vite, Tailwind CSS, Zustand |
| Backend | Python, FastAPI, SQLAlchemy (sync), SQLite |
| AI | Anthropic Claude (`claude-sonnet-4-6` default) and OpenAI (`gpt-4o` default), user-selectable |
| Documents | `python-docx`, PyMuPDF, openpyxl |
| Secrets | `keyring` (OS credential store) |
| Desktop | Electron + electron-builder, PyInstaller |

---

## Getting started

There are two ways to run MaximoBRD, with **different requirements** depending on who you are:

### For end users (installed app)

You do **not** need the repo, a terminal, Python, or Node. You need only:

- **macOS** (the packaged build is currently macOS-only)
- The **`MaximoBRD-<version>.dmg`** installer (built by a developer with `npm run build:mac`)
- An API key from [Anthropic](https://platform.claude.com/) and/or [OpenAI](https://platform.openai.com/)

Install: double-click the DMG → drag **MaximoBRD** into Applications → **right-click the app → Open** the first time (it's unsigned, so a normal double-click is blocked by Gatekeeper) → then add your API key under **Settings**. Everything runs locally; the backend is bundled inside the app.

### For developers (running from the repo)

To run from a clone you need:

- **Node.js 20+**
- **Python 3.11+**
- An API key from [Anthropic](https://platform.claude.com/) and/or [OpenAI](https://platform.openai.com/)

The `start.sh` script (below) checks the Node and Python versions for you, but it **cannot install them** — make sure both are present first.

### Quick start (one command)

From the repo root:

```bash
./start.sh
```

This checks your Node and Python versions, installs the backend (Python venv) and frontend packages the first time, builds the UI, and starts the app at **http://127.0.0.1:8765**. Re-running it is safe and fast — completed setup steps are skipped. (`npm start` runs the same script.)

> The script can't install Node or Python for you — if either is missing or too old, it prints exactly what to install and stops.

### First-time setup (manual)

If you'd rather set things up by hand:

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

### Run in the browser (development)

Two terminals:

```bash
# Terminal 1 — backend (auto-reload)
cd backend && source .venv/bin/activate
uvicorn main:app --reload --port 8765

# Terminal 2 — frontend (proxies /api → 8765)
cd frontend && npm run dev
```

Open **http://localhost:5173**.

Single-command alternative (one terminal, one URL) — builds the UI and lets FastAPI serve it:

```bash
npm run app          # from the repo root → http://127.0.0.1:8765
```

### Run as the desktop app (development)

```bash
npm run dev:electron   # builds the UI, then opens the Electron window
```

### First use
1. Open **Settings**, pick a provider, paste your API key, and click **Test Connection**.
2. Create a project, upload a document or two, and click **Generate**.

---

## Building the installer

```bash
npm run build:mac      # → release/MaximoBRD-<version>.dmg
```

This builds the frontend, freezes the backend with PyInstaller, then packages everything into a macOS DMG. The app is currently **unsigned** — on first launch, right-click → **Open** to clear Gatekeeper.

> A Windows (NSIS `.exe`) target is configured but must be built **on Windows** — PyInstaller cannot cross-compile. See [Potential enhancements](#potential-enhancements).

---

## Testing

```bash
npm run test:backend   # pytest — processors, ID assignment, DOCX render, pipeline, etc.
```

---

## Project structure

```
maximobrd/
├── frontend/        React UI (pages, store, single api.js layer)
├── backend/         FastAPI app
│   ├── routes/      REST + SSE endpoints
│   ├── agents/      pipeline stages (extractor → summarizer → analyzer → generator)
│   ├── services/    LLM client, DOCX renderer, keychain, progress bus
│   ├── processors/  per-filetype text extraction
│   ├── prompts/     LLM prompt templates
│   ├── templates/   default BRD structure (JSON)
│   └── tests/       pytest suite
├── knowledge/versions/   Maximo version facts (injected into prompts, never hardcoded)
├── electron/        desktop shell (main.js, preload.js, builder config)
└── docs/            blueprint.md (vision) + implementation-spec.md (authoritative)
```

**Authoritative reference:** [`docs/implementation-spec.md`](docs/implementation-spec.md) holds the full schemas, API contracts, prompts, and milestone plan.

---

## Configuration

Sensible defaults; override via environment variables (see `backend/config.py`).

| Variable | Default | Purpose |
|----------|---------|---------|
| `MAXIMOBRD_PORT` | `8765` | Backend port (the desktop shell picks a free one automatically) |
| `TOKEN_THRESHOLD` | `12000` | Character count above which a source is summarized first |
| `MAX_UPLOAD_BYTES` | `524288000` (500 MB) | Upload size cap |
| `APP_DATA_DIR` | OS-specific | Where `app.db` lives |
| `PROJECTS_DEFAULT_DIR` | `~/MaximoBRD` | Default root for new project folders |

---

## Security & privacy

- **API keys** are stored only in the OS credential store via `keyring` — never in the database, logs, code, or `.env`.
- The backend binds to **`127.0.0.1` only** — it is not reachable from the network.
- Only **extracted text** is sent to AI providers — never raw audio, video, or binary files.
- Maximo version facts live in `knowledge/versions/*.md` and are injected at runtime, keeping the codebase free of hardcoded product claims.

---

## Potential enhancements

Ideas that build on the current foundation. None are started yet.

### 1. Run the desktop app on Windows
The architecture is already cross-platform (the backend resolves `%APPDATA%`, and `keyring` uses Windows Credential Locker automatically), and an NSIS `.exe` target is configured in `electron/package.json`. To ship a Windows build:
- Build the backend with PyInstaller **on a Windows machine** (or a `windows-latest` CI runner) — it cannot be cross-compiled from macOS; this produces `maximobrd-backend.exe`.
- Append `.exe` to the bundled backend path in `electron/main.js` when running on `win32`, and use `.venv\Scripts\python.exe` for the dev path.
- Add a `build:win` script (`electron-builder --win`) and run it on Windows.

> This is the formal Milestone 8 deliverable. An interim alternative is to ship the PyInstaller `maximobrd-backend.exe` alone and open `127.0.0.1:<port>` in a browser — simpler, but it loses the native window, icon, and clean install/quit.

### 2. Dark mode
The UI already uses Tailwind. Add a theme toggle (Tailwind's `dark:` variant + a Zustand-held theme flag, applied as a `class` on `<html>`). Keep it in app state per the no-`localStorage` rule, or persist a single preference server-side via Settings.

### 3. Friendlier "Test Connection" error messages
Today a failed connection test surfaces the raw provider error. Map common failures to plain guidance in `services/llm_client.py` / the settings route — e.g. *"That API key was rejected — check it's the right provider and hasn't expired"* for a 401, *"You've hit your provider's rate limit, try again shortly"* for a 429, and *"Couldn't reach the provider — check your internet connection"* for a network error.

### 4. Simpler Maximo version selection
The picker currently lists `Maximo 7.6.0.x` and `Maximo 7.6.1.x` separately. Collapse these into a single **Maximo 7.6** option, leaving three clear choices: **Maximo 7.6**, **MAS 8.x**, and **MAS 9.x**. This is a small change to `VERSION_MAP` in `backend/config.py` and the version list in `frontend/src/pages/ProjectList.jsx` (both 7.6 entries already point at the same `maximo-76.md` knowledge file). *(MAS 8.x ships its knowledge file and is enabled in Milestone 5.)*

### 5. Let the user choose where project files are saved
The New Project modal pre-fills the folder path from `PROJECTS_DEFAULT_DIR` (`~/MaximoBRD`) as editable text. Improve this with a real folder picker:
- **Browser:** the File System Access API directory picker (where supported).
- **Desktop:** wire Electron's native `dialog.showOpenDialog` through a small `preload.js` bridge so users can browse to any location (e.g. a OneDrive- or Dropbox-synced folder).

---

## Roadmap

Milestones 0–4 are complete. Remaining work, per [`docs/implementation-spec.md`](docs/implementation-spec.md) §18:

| Milestone | Scope | Status |
|-----------|-------|--------|
| 0 — Scaffold | Repo, health check, prerequisite artifacts | ✅ Complete |
| 1 — Working MVP | Project CRUD, upload + extraction, AI pipeline, DOCX export | ✅ Complete |
| 2 — Hardening | Cancel/retry, branded templates, timestamp overrides, structured errors | ✅ Complete |
| 3 — Desktop shell | Electron app + macOS DMG, same-origin design, PyInstaller backend | ✅ Complete |
| 4 — Second provider | OpenAI support (pulled forward into M1) | ✅ Complete |
| **5 — Media + MAS 8** | `mas-8.md` knowledge + UI enablement; audio/video/image processors (Whisper, ffmpeg, vision) with `PENDING → TRANSCRIBING → EXTRACTED` | ⏳ Next |
| **6 — Branding clone** | Extract and apply a client's fonts/logo/table styling to the DOCX | ⏳ Planned |
| **7 — Ollama** | Local-model provider in `LLMClient` + model-discovery Settings UI | ⏳ Planned |
| **8 — Windows + polish** | Windows installer (electron-builder + PyInstaller), native file dialogs, onboarding, accessibility, optional code signing | ⏳ Planned |

---

## Documentation

| Document | Role |
|----------|------|
| [`docs/implementation-spec.md`](docs/implementation-spec.md) | **Authoritative** build spec — schemas, API contracts, prompts, milestones |
| [`docs/blueprint.md`](docs/blueprint.md) | Product vision and constraints (reference only) |
| [`CLAUDE.md`](CLAUDE.md) | Project rules and conventions |

---

## License

UNLICENSED — internal/private project.
</content>
</invoke>
