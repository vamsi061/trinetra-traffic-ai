#!/usr/bin/env bash
set -e

# ─── TRINETRA AI — One-Command Launcher ──────────────────────────────
# Usage:  bash start.sh              (production — built frontend)
#         bash start.sh --dev        (development — frontend hot-reload)
#         bash start.sh --install    (install deps only)
# ───────────────────────────────────────────────────────────────────────

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
VENV_DIR="$ROOT_DIR/venv"

# Auto-detect Python (python3 on macOS/Linux, python on Windows/Git Bash)
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        PYTHON="$cmd"
        break
    fi
done

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC}  $1"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $1"; exit 1; }

# ─── Dependency Checks ────────────────────────────────────────────────
check_cmd() {
    if ! command -v "$1" &>/dev/null; then
        fail "$1 is not installed. Install it first."
    fi
}

install_python_deps() {
    if [ ! -d "$VENV_DIR" ]; then
        info "Creating Python virtual environment..."
        $PYTHON -m venv "$VENV_DIR"
        ok "Virtual environment created"
    fi

    source "$VENV_DIR/bin/activate"
    $PYTHON -m pip install --upgrade pip -q 2>/dev/null

    info "Installing/verifying Python dependencies..."
    pip install -r "$BACKEND_DIR/requirements.txt"
    ok "Python dependencies ready"

    check_helmet_model
}

check_helmet_model() {
    MODEL_FILE="$BACKEND_DIR/models/helmet_yolov8n.pt"
    if [ -f "$MODEL_FILE" ]; then
        SIZE_MB=$(du -sm "$MODEL_FILE" | cut -f1)
        ok "Helmet model found ($SIZE_MB MB)"
    else
        warn "Helmet model not found — downloading from Hugging Face..."
        source "$VENV_DIR/bin/activate"
        python "$BACKEND_DIR/download_helmet_model.py"
        if [ -f "$MODEL_FILE" ]; then
            ok "Helmet model downloaded"
        else
            fail "Failed to download helmet model"
        fi
    fi
}

install_frontend_deps() {
    info "Checking Node.js dependencies..."
    if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
        info "Installing frontend dependencies..."
        cd "$FRONTEND_DIR"
        npm install --quiet 2>&1 | tail -1
        ok "Frontend dependencies installed"
    else
        ok "Node.js dependencies satisfied"
    fi
}

build_frontend() {
    info "Building frontend for production..."
    cd "$FRONTEND_DIR"
    npm run build 2>&1 | tail -3
    ok "Frontend built at $FRONTEND_DIR/dist"
}

# ─── Service Starters ─────────────────────────────────────────────────
start_backend() {
    info "Starting FastAPI backend on http://0.0.0.0:8000 ..."
    source "$VENV_DIR/bin/activate"
    cd "$BACKEND_DIR"
    uvicorn main:app --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
    sleep 3
    if kill -0 "$BACKEND_PID" 2>/dev/null; then
        ok "Backend running (PID $BACKEND_PID)"
    else
        fail "Backend failed to start"
    fi
}

start_frontend_dev() {
    info "Starting frontend dev server on http://localhost:5173 ..."
    cd "$FRONTEND_DIR"
    npm run dev &
    FRONTEND_PID=$!
    sleep 3
    if kill -0 "$FRONTEND_PID" 2>/dev/null; then
        ok "Frontend dev server running (PID $FRONTEND_PID)"
    else
        fail "Frontend dev server failed to start"
    fi
}

# ─── Cleanup ──────────────────────────────────────────────────────────
cleanup() {
    echo ""
    warn "Shutting down services..."
    [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null && ok "Backend stopped"
    [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null && ok "Frontend stopped"
    exit 0
}
trap cleanup SIGINT SIGTERM

# ─── Main ─────────────────────────────────────────────────────────────
clear
echo -e "${RED}"
echo "  ╔══════════════════════════════════════════╗"
echo "  ║        TRINETRA AI — Launcher v2         ║"
echo "  ║  Traffic Violation Detection Platform    ║"
echo "  ╚══════════════════════════════════════════╝"
echo -e "${NC}"

# Check system requirements
if [ -z "$PYTHON" ]; then
    fail "Python is not installed. Install Python 3.8+ first."
fi
check_cmd "node"
check_cmd "npm"

# Install mode
if [ "$1" == "--install" ]; then
    install_python_deps
    install_frontend_deps
    build_frontend
    ok "All dependencies installed. Run 'bash start.sh' to start."
    exit 0
fi

# Create data directories
mkdir -p "$ROOT_DIR/data/uploads" "$ROOT_DIR/data/evidence" "$ROOT_DIR/data/reports"

# Install everything
install_python_deps
install_frontend_deps

# Dev mode — separate servers with hot reload
if [ "$1" == "--dev" ]; then
    warn "Starting in DEVELOPMENT mode (hot reload enabled)"
    start_backend
    start_frontend_dev
    echo ""
    echo -e "${GREEN}  ─── TRINETRA AI is RUNNING ───${NC}"
    echo -e "  Frontend:  ${CYAN}http://localhost:5173${NC}"
    echo -e "  Backend:   ${CYAN}http://localhost:8000${NC}"
    echo -e "  API Docs:  ${CYAN}http://localhost:8000/docs${NC}"
    echo ""
    echo "  Press Ctrl+C to stop all services"
    wait
fi

# Production mode — build frontend, serve from FastAPI
build_frontend
start_backend

echo ""
echo -e "${GREEN}  ─── TRINETRA AI is RUNNING ───${NC}"
echo -e "  App:       ${CYAN}http://localhost:8000${NC}"
echo -e "  API Docs:  ${CYAN}http://localhost:8000/docs${NC}"
echo ""
echo "  Press Ctrl+C to stop"
wait
