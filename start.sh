
#!/usr/bin/env bash
set -Eeuo pipefail

# ============================================================
# Datathon - Local Development Launcher
# Supports macOS and Ubuntu
#
# Usage:
#   ./start.sh setup
#   ./start.sh ingest
#   ./start.sh backend
#   ./start.sh dashboard
#   ./start.sh all
# ============================================================

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

VENV_DIR="$ROOT_DIR/.venv"

INGESTION_DIR="$ROOT_DIR/ingestion"
INGESTION_SCRIPT="$INGESTION_DIR/ingest.py"

BACKEND_DIR="$ROOT_DIR/backend/spring-boot"

DASHBOARD_DIR="$ROOT_DIR/dashboard/streamlit"
DASHBOARD_APP="$DASHBOARD_DIR/app.py"

BACKEND_PID=""

log() {
    printf '[Datathon] %s\n' "$*"
}

fail() {
    printf '[Datathon] ERROR: %s\n' "$*" >&2
    exit 1
}

require_command() {
    command -v "$1" >/dev/null 2>&1 ||
        fail "Required command not found: $1"
}

# ------------------------------------------------------------
# Python environment
# ------------------------------------------------------------

setup_python() {
    require_command python3

    if [[ ! -d "$VENV_DIR" ]]; then
        log "Creating Python virtual environment..."
        python3 -m venv "$VENV_DIR"
    fi

    local python="$VENV_DIR/bin/python"

    log "Installing Python dependencies..."

    "$python" -m pip install --upgrade pip

    # Core data pipeline dependencies
    "$python" -m pip install \
        boto3 \
        duckdb \
        pandas \
        python-dotenv

    # Optional project-specific dependencies
    if [[ -f "$INGESTION_DIR/requirements.txt" ]]; then
        "$python" -m pip install \
            -r "$INGESTION_DIR/requirements.txt"
    fi

    if [[ -f "$DASHBOARD_DIR/requirements.txt" ]]; then
        "$python" -m pip install \
            -r "$DASHBOARD_DIR/requirements.txt"
    else
        "$python" -m pip install streamlit requests
    fi

    log "Python environment is ready."
}

ensure_python() {
    if [[ ! -x "$VENV_DIR/bin/python" ]]; then
        fail "Python environment not found. Run: ./start.sh setup"
    fi
}

# ------------------------------------------------------------
# Ingestion: Amazon S3 -> Python -> DuckDB
# ------------------------------------------------------------

run_ingestion() {
    ensure_python

    [[ -f "$INGESTION_SCRIPT" ]] ||
        fail "Ingestion script not found: $INGESTION_SCRIPT"

    log "Starting S3 -> DuckDB ingestion..."

    # Avoid exposing AWS keys in this script.
    # boto3 uses the standard AWS credential chain.
    (
        cd "$ROOT_DIR"
        "$VENV_DIR/bin/python" "$INGESTION_SCRIPT"
    )

    log "Ingestion finished."
}

# ------------------------------------------------------------
# Spring Boot REST API
# ------------------------------------------------------------

run_backend() {
    [[ -f "$BACKEND_DIR/pom.xml" ]] ||
        fail "Spring Boot pom.xml not found: $BACKEND_DIR/pom.xml"

    log "Starting Spring Boot backend..."

    cd "$BACKEND_DIR"

    if [[ -f "./mvnw" ]]; then
        bash ./mvnw spring-boot:run
    else
        require_command mvn
        mvn spring-boot:run
    fi
}

# ------------------------------------------------------------
# Streamlit dashboard
# ------------------------------------------------------------

run_dashboard() {
    ensure_python

    [[ -f "$DASHBOARD_APP" ]] ||
        fail "Dashboard app not found: $DASHBOARD_APP"

    log "Starting Streamlit dashboard..."

    cd "$ROOT_DIR"

    "$VENV_DIR/bin/python" -m streamlit run \
        "$DASHBOARD_APP" \
        --server.port 8501
}

# ------------------------------------------------------------
# Run backend and dashboard together
# ------------------------------------------------------------

cleanup() {
    log "Stopping development services..."

    if [[ -n "$BACKEND_PID" ]]; then
        kill "$BACKEND_PID" 2>/dev/null || true
        wait "$BACKEND_PID" 2>/dev/null || true
    fi
}

run_all() {
    ensure_python
    require_command java

    [[ -f "$BACKEND_DIR/pom.xml" ]] ||
        fail "Spring Boot backend is not ready."

    [[ -f "$DASHBOARD_APP" ]] ||
        fail "Streamlit dashboard is not ready."

    trap cleanup EXIT INT TERM

    log "Starting backend in the background..."

    run_backend &
    BACKEND_PID=$!

    log "Starting dashboard..."

    run_dashboard
}

# ------------------------------------------------------------
# CLI
# ------------------------------------------------------------

show_help() {
    cat <<'EOF'
Datathon Development Launcher

Usage:
  ./start.sh <command>

Commands:
  setup       Create Python environment and install dependencies
  ingest      Download S3 CSV and load it into DuckDB
  backend     Start the Spring Boot REST API
  dashboard   Start the Streamlit dashboard
  all         Start Spring Boot and Streamlit together
  help        Show this help message

Examples:
  ./start.sh setup
  ./start.sh ingest
  ./start.sh all

EOF
}

case "${1:-help}" in
    setup)
        setup_python
        ;;
    ingest)
        run_ingestion
        ;;
    backend)
        run_backend
        ;;
    dashboard)
        run_dashboard
        ;;
    all)
        run_all
        ;;
    help|-h|--help)
        show_help
        ;;
    *)
        show_help
        fail "Unknown command: $1"
        ;;
esac