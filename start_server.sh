#!/bin/bash
# ETF Tracking System - Server startup script (local SQLite mode)
DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$DIR/.venv/bin/uvicorn" app.main:app --host 127.0.0.1 --port 8000
