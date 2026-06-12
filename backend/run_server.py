"""Standalone backend launcher.

The Electron shell spawns this (as a PyInstaller binary in production, or via the
dev venv during development). It starts uvicorn programmatically on the port the
shell chose, binding to 127.0.0.1 only. Unlike `uvicorn main:app` on the CLI, this
has no reload and works when frozen into a single executable.
"""
import os

import uvicorn

from main import app


def main() -> None:
    port = int(os.environ.get("MAXIMOBRD_PORT", "8765"))
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()
