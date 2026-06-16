#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$ROOT_DIR/../trinetra-venv"
PYTHON="$VENV/bin/python"

if [ ! -f "$PYTHON" ]; then
    echo "Creating venv..."
    python3 -m venv "$VENV"
    "$PYTHON" -m pip install -q -r "$ROOT_DIR/requirements.txt"
fi

cd "$ROOT_DIR"
echo ""
echo "========================================"
echo "  TRINETRA AI — Unit Tests"
echo "========================================"
echo ""

if ! "$PYTHON" -c "import pytest" 2>/dev/null; then
    "$PYTHON" -m pip install -q pytest pytest-asyncio httpx
fi

"$PYTHON" -m pytest tests/ \
    -v \
    --tb=short \
    --disable-warnings \
    -x \
    "$@"

echo ""
echo "========================================"
echo "  All unit tests complete"
echo "========================================"
