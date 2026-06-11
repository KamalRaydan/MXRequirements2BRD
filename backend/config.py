"""Central configuration. All values overridable via environment variables (spec §15)."""
import os
from pathlib import Path

# Where this backend package lives (used to find prompts/, templates/, knowledge/)
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

# app.db lives in the OS app-data dir (macOS: ~/Library/Application Support/MaximoBRD)
_default_app_data = Path.home() / "Library" / "Application Support" / "MaximoBRD"
APP_DATA_DIR = Path(os.environ.get("APP_DATA_DIR", str(_default_app_data)))

# Default root for new project folders
PROJECTS_DEFAULT_DIR = Path(os.environ.get("PROJECTS_DEFAULT_DIR", str(Path.home() / "MaximoBRD")))

KNOWLEDGE_DIR = REPO_DIR / "knowledge" / "versions"
PROMPTS_DIR = BACKEND_DIR / "prompts"
TEMPLATES_DIR = BACKEND_DIR / "templates"

APP_VERSION = "0.1.0"

# Maximo version key -> (UI label, knowledge filename, enabled in MVP)
VERSION_MAP = {
    "maximo-760": ("Maximo 7.6.0.x", "maximo-76.md", True),
    "maximo-761": ("Maximo 7.6.1.x", "maximo-76.md", True),
    "mas-8": ("MAS 8.x", "mas-8.md", False),
    "mas-9": ("MAS 9.x", "mas-9.md", True),
}

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
