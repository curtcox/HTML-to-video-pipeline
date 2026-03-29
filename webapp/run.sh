#!/bin/bash
# Start the HTML-to-Video Pipeline web app via fsrouter.
#
# Sets PIPELINE_ROOT so handlers can find pipeline modules and output dir.
# Sets PYTHONPATH so handlers can `import config`, `import parse_article`, etc.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_PYTHON="$REPO_ROOT/venv/bin/python3"

if [ -x "$VENV_PYTHON" ]; then
    export PATH="$REPO_ROOT/venv/bin:$PATH"
    PYTHON="$VENV_PYTHON"
else
    echo "Error: project virtualenv not found at $REPO_ROOT/venv"
    echo "Run ./install.sh first, then start the web app again."
    exit 1
fi

export PIPELINE_ROOT="$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT:${PYTHONPATH:-}"
export ROUTE_DIR="$SCRIPT_DIR/routes"
export COMMAND_TIMEOUT="${COMMAND_TIMEOUT:-5400}"

echo "Pipeline root: $PIPELINE_ROOT"
echo "Route dir:     $ROUTE_DIR"
echo "Python:        $PYTHON"
echo "Starting at    http://localhost:${PORT:-8080}"

exec "$PYTHON" "$SCRIPT_DIR/fsrouter.py"
