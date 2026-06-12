"""Central configuration. All values overridable via environment variables (spec §15)."""
import os
import sys
from pathlib import Path

# When packaged by PyInstaller, `sys.frozen` is set and bundled data files (prompts,
# templates, knowledge, the built frontend) live under `sys._MEIPASS`. In normal dev
# runs we resolve those relative to this source file.
FROZEN = getattr(sys, "frozen", False)
if FROZEN:
    _BUNDLE_DIR = Path(getattr(sys, "_MEIPASS"))
    BACKEND_DIR = _BUNDLE_DIR
    REPO_DIR = _BUNDLE_DIR
else:
    BACKEND_DIR = Path(__file__).resolve().parent
    REPO_DIR = BACKEND_DIR.parent

PORT = int(os.environ.get("MAXIMOBRD_PORT", "8765"))

# Chars before a source gets summarized instead of passed whole
TOKEN_THRESHOLD = int(os.environ.get("TOKEN_THRESHOLD", "12000"))

# 500 MB upload cap
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", str(500 * 1024 * 1024)))

LLM_MAX_TOKENS_SUMMARIZE = int(os.environ.get("LLM_MAX_TOKENS_SUMMARIZE", "4096"))
LLM_MAX_TOKENS_ANALYZE = int(os.environ.get("LLM_MAX_TOKENS_ANALYZE", "8192"))
LLM_MAX_TOKENS_GENERATE = int(os.environ.get("LLM_MAX_TOKENS_GENERATE", "8192"))

# app.db lives in the OS-specific application-data dir. Cross-platform so the same
# backend runs under the Electron shell on macOS, Windows, and Linux (the keyring
# library separately picks the matching OS credential store for the API key).
def _default_app_data_dir() -> Path:
    home = Path.home()
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", str(home / "AppData" / "Roaming")))
    elif sys.platform == "darwin":
        base = home / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", str(home / ".local" / "share")))
    return base / "MaximoBRD"


APP_DATA_DIR = Path(os.environ.get("APP_DATA_DIR", str(_default_app_data_dir())))

# Default root for new project folders
PROJECTS_DEFAULT_DIR = Path(os.environ.get("PROJECTS_DEFAULT_DIR", str(Path.home() / "MaximoBRD")))

KNOWLEDGE_DIR = REPO_DIR / "knowledge" / "versions"
PROMPTS_DIR = BACKEND_DIR / "prompts"
TEMPLATES_DIR = BACKEND_DIR / "templates"

# Built React app served at "/". Bundled into the PyInstaller binary (frozen) or read
# from frontend/dist in dev; overridable so the Electron shell can point elsewhere.
_frontend_dist_env = os.environ.get("MAXIMOBRD_FRONTEND_DIST")
if _frontend_dist_env:
    FRONTEND_DIST = Path(_frontend_dist_env)
elif FROZEN:
    FRONTEND_DIST = BACKEND_DIR / "frontend_dist"
else:
    FRONTEND_DIST = REPO_DIR / "frontend" / "dist"

APP_VERSION = "0.1.0"

# Maximo version key -> (UI label, knowledge filename, enabled in MVP)
VERSION_MAP = {
    "maximo-76": ("Maximo 7.6.x", "maximo-76.md", True),
    "mas-8": ("MAS 8.x", "mas-8.md", False),
    "mas-9": ("MAS 9.x", "mas-9.md", True),
}

# Projects created before the 7.6 entries were merged may still store these keys.
LEGACY_VERSION_KEYS = {"maximo-760": "maximo-76", "maximo-761": "maximo-76"}

# Allowed module codes for BRD-{MODULE}-{NNN} IDs (spec §7.5)
MODULE_CODES = [
    "WO", "ASSET", "INV", "PURCH", "PM", "SR", "LABOR", "CAL", "BUDGET",
    "METER", "ROUTES", "SLA", "LOC", "PERSON", "COMP", "SAFETY", "CONTRACT",
    "RFQ", "REORDER", "GL", "ESCALATION", "KPI", "MOBILE", "INTEGRATION", "GENERAL",
]

# Supported AI providers. models_url is shown in Settings so users can look up model names.
PROVIDERS = {
    "anthropic": {
        "label": "Anthropic Claude",
        "default_model": "claude-sonnet-4-6",
        "models_url": "https://platform.claude.com/docs/en/about-claude/models/overview",
    },
    "openai": {
        "label": "OpenAI",
        "default_model": "gpt-4o",
        "models_url": "https://platform.openai.com/docs/models",
    },
}

# API key location in the macOS Keychain (MVP; Electron safeStorage in Milestone 3).
# One Keychain entry per provider: account name is "api_key_{provider}".
KEYRING_SERVICE = "maximobrd"
KEYRING_LEGACY_ACCOUNT = "api_key"  # pre-multi-provider entry, read as anthropic
