#!/bin/sh
# MaximoBRD one-command bootstrap + launcher.
#
# Run this after cloning:  ./start.sh
# It sets up anything that's missing (Python venv, npm packages), then starts
# the app at http://127.0.0.1:8765. Re-running is safe and fast — finished
# setup steps are skipped.

set -e  # stop on the first error

# Move to the repo root (the folder this script lives in), so the script works
# no matter what directory you call it from.
cd "$(dirname "$0")"

echo "MaximoBRD setup"
echo "==============="

# --- 1. Check the two runtimes we cannot install for you ---------------------

# Node.js 20+ : `node -v` prints like "v22.14.0"; cut out the major number.
if ! command -v node >/dev/null 2>&1; then
  echo "ERROR: Node.js is not installed."
  echo "Install Node 20 or newer from https://nodejs.org/ and run this again."
  exit 1
fi
NODE_MAJOR=$(node -v | sed 's/^v//' | cut -d. -f1)
if [ "$NODE_MAJOR" -lt 20 ]; then
  echo "ERROR: Node.js 20+ is required (you have $(node -v))."
  echo "Update from https://nodejs.org/ and run this again."
  exit 1
fi

# Python 3.11+ : the system `python3` may be too old, so try a few names and
# keep the first one that reports 3.11 or newer.
PYTHON=""
for CANDIDATE in python3.13 python3.12 python3.11 python3 python; do
  if command -v "$CANDIDATE" >/dev/null 2>&1; then
    # Ask Python itself whether it is >= 3.11; exit code 0 means yes.
    if "$CANDIDATE" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
      PYTHON="$CANDIDATE"
      break
    fi
  fi
done
if [ -z "$PYTHON" ]; then
  echo "ERROR: Python 3.11 or newer is required and was not found."
  echo "Install it from https://www.python.org/downloads/ and run this again."
  exit 1
fi

echo "Using Node $(node -v) and $("$PYTHON" --version)"

# --- 2. Backend: create the virtual environment + install packages -----------
# Only do this the first time — if backend/.venv already exists, we skip it.

if [ ! -d backend/.venv ]; then
  echo "Creating Python virtual environment and installing backend packages..."
  "$PYTHON" -m venv backend/.venv
  backend/.venv/bin/pip install --upgrade pip >/dev/null
  backend/.venv/bin/pip install -r backend/requirements.txt
else
  echo "Backend packages already installed — skipping."
fi

# --- 3. Frontend: install npm packages ---------------------------------------
# Skip if node_modules is already there.

if [ ! -d frontend/node_modules ]; then
  echo "Installing frontend packages..."
  (cd frontend && npm install)
else
  echo "Frontend packages already installed — skipping."
fi

# --- 4. Build the UI and start the app ---------------------------------------
# `npm run app` builds the React UI and starts FastAPI, which serves that UI
# and the API together at one URL.

echo ""
echo "Setup complete. Starting MaximoBRD at http://127.0.0.1:8765"
echo "(Press Ctrl+C to stop.)"
echo ""
npm run app
