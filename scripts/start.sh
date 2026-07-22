#!/usr/bin/env sh
# Local / PaaS start — honors PORT for Render/Railway/Fly
set -eu
PORT="${PORT:-8000}"
exec uvicorn backend.app.main:app --host 0.0.0.0 --port "$PORT"
