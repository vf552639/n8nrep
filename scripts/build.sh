#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "=== Phase 1 build ==="

# 1. Frontend
echo "--- Building frontend ---"
cd frontend
npm ci
npm run build
cd "$ROOT"

# 2. Python sidecar (PyInstaller)
echo "--- Building Python sidecar ---"
pip install pyinstaller>=6.5.0
pyinstaller \
  --onefile \
  --name sidecar \
  --add-data "alembic:alembic" \
  --add-data "alembic.ini:." \
  --hidden-import aiosqlite \
  --hidden-import app.models \
  app/main.py

mkdir -p resources
cp dist/sidecar resources/sidecar

# 3. Electron
echo "--- Building Electron app ---"
cd electron
npm ci
npm run build:electron
cd "$ROOT"

npm run dist

echo "=== Build complete → release/ ==="
