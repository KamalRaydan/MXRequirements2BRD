# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the MaximoBRD backend (spec §13.2 / §13.4).
#
# Produces a self-contained backend the Electron shell spawns: the FastAPI app +
# uvicorn + every data file it reads at runtime (prompts, templates, Maximo knowledge,
# and the built React frontend served at "/"). Onedir build → backend/dist/maximobrd-backend/.
#
# Build:  cd backend && .venv/bin/python -m PyInstaller --noconfirm maximobrd-backend.spec
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

backend_dir = Path(SPECPATH)          # SPECPATH: dir of this spec, injected by PyInstaller
repo_dir = backend_dir.parent

# (source on disk, destination inside the bundle) — must match the frozen paths in config.py
datas = [
    (str(backend_dir / "prompts"), "prompts"),
    (str(backend_dir / "templates"), "templates"),
    (str(repo_dir / "knowledge" / "versions"), "knowledge/versions"),
    (str(repo_dir / "frontend" / "dist"), "frontend_dist"),
]
binaries = []
hiddenimports = []

# These pull in data files, native libs, and/or dynamically-discovered submodules
# (keyring's OS credential backends, the SDK token data, PyMuPDF's native lib,
# uvicorn's protocol implementations) that PyInstaller's static analysis misses.
for pkg in ("keyring", "anthropic", "openai", "pymupdf", "uvicorn"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

# SQLAlchemy loads its dialect modules lazily by name.
hiddenimports += collect_submodules("sqlalchemy.dialects.sqlite")

a = Analysis(
    ["run_server.py"],
    pathex=[str(backend_dir)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="maximobrd-backend",
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="maximobrd-backend",
)
