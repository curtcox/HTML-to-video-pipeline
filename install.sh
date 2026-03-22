#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# --- Python version check ---
REQUIRED_MAJOR=3
REQUIRED_MINOR=10
MAX_MINOR=13

PYTHON=${PYTHON:-python3}

if ! command -v "$PYTHON" &>/dev/null; then
    echo "Error: $PYTHON not found. Install Python ${REQUIRED_MAJOR}.${REQUIRED_MINOR}–${REQUIRED_MAJOR}.${MAX_MINOR}."
    exit 1
fi

PY_VERSION=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$("$PYTHON" -c "import sys; print(sys.version_info.major)")
PY_MINOR=$("$PYTHON" -c "import sys; print(sys.version_info.minor)")

if [ "$PY_MAJOR" -ne "$REQUIRED_MAJOR" ] || [ "$PY_MINOR" -lt "$REQUIRED_MINOR" ] || [ "$PY_MINOR" -gt "$MAX_MINOR" ]; then
    if command -v pyenv &>/dev/null; then
        PYENV_PYTHON=$(pyenv which python3 2>/dev/null || true)
        if [ -n "$PYENV_PYTHON" ] && [ -x "$PYENV_PYTHON" ]; then
            PYENV_VERSION=$("$PYENV_PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
            PYENV_MAJOR=$("$PYENV_PYTHON" -c "import sys; print(sys.version_info.major)")
            PYENV_MINOR=$("$PYENV_PYTHON" -c "import sys; print(sys.version_info.minor)")
            if [ "$PYENV_MAJOR" -eq "$REQUIRED_MAJOR" ] && [ "$PYENV_MINOR" -ge "$REQUIRED_MINOR" ] && [ "$PYENV_MINOR" -le "$MAX_MINOR" ]; then
                echo "Using pyenv Python $PYENV_VERSION at $PYENV_PYTHON"
                PYTHON="$PYENV_PYTHON"
                PY_VERSION="$PYENV_VERSION"
                PY_MAJOR="$PYENV_MAJOR"
                PY_MINOR="$PYENV_MINOR"
            else
                echo "Error: Python ${REQUIRED_MAJOR}.${REQUIRED_MINOR}–${REQUIRED_MAJOR}.${MAX_MINOR} required (found $PY_VERSION)."
                echo "Tip: python3 is not using your pyenv version yet."
                echo "  Current pyenv python3: $PYENV_PYTHON ($PYENV_VERSION)"
                echo "  Run:"
                echo "    PYTHON=\"$PYENV_PYTHON\" ./install.sh"
                echo "  Or make pyenv shims active in your shell, then rerun ./install.sh"
                exit 1
            fi
        else
            echo "Error: Python ${REQUIRED_MAJOR}.${REQUIRED_MINOR}–${REQUIRED_MAJOR}.${MAX_MINOR} required (found $PY_VERSION)."
            echo "Tip: use pyenv to install a compatible version, or set PYTHON=python3.12"
            echo "  Example with pyenv:"
            echo "    pyenv install 3.12.10"
            echo "    pyenv local 3.12.10"
            echo "    ./install.sh"
            echo "  Or run:"
            echo "    PYTHON=python3.12 ./install.sh"
            exit 1
        fi
    else
        echo "Error: Python ${REQUIRED_MAJOR}.${REQUIRED_MINOR}–${REQUIRED_MAJOR}.${MAX_MINOR} required (found $PY_VERSION)."
        echo "Tip: use pyenv to install a compatible version, or set PYTHON=python3.12"
        echo "  Example with pyenv:"
        echo "    pyenv install 3.12.10"
        echo "    pyenv local 3.12.10"
        echo "    ./install.sh"
        echo "  Or run:"
        echo "    PYTHON=python3.12 ./install.sh"
        exit 1
    fi
fi
echo "Python $PY_VERSION ✓"

# --- ffmpeg check ---
if ! command -v ffmpeg &>/dev/null; then
    echo "Error: ffmpeg not found."
    echo "  macOS:  brew install ffmpeg"
    echo "  Linux:  sudo apt install ffmpeg"
    exit 1
fi
echo "ffmpeg ✓"

# --- Create venv ---
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    "$PYTHON" -m venv venv
fi
source venv/bin/activate
echo "venv activated ($(python --version))"

# --- Core dependencies ---
echo "Installing core dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

# --- Optional TTS backends ---
echo ""
echo "Optional TTS backends:"
echo "  1) say     — macOS built-in (no install needed)"
echo "  2) kokoro  — local neural TTS, 82M params"
echo "  3) piper   — local neural TTS"
echo "  4) elevenlabs — cloud API"
echo ""
read -p "Install extra TTS backends? [comma-separated, e.g. 2,4 or 'none'] " TTS_CHOICE

if [ -n "$TTS_CHOICE" ] && [ "$TTS_CHOICE" != "none" ]; then
    IFS=',' read -ra CHOICES <<< "$TTS_CHOICE"
    for choice in "${CHOICES[@]}"; do
        choice=$(echo "$choice" | tr -d ' ')
        case "$choice" in
            2|kokoro)
                echo "Installing Kokoro dependencies..."
                # Check espeak-ng
                if ! command -v espeak-ng &>/dev/null; then
                    echo "  Warning: espeak-ng not found. Kokoro needs it."
                    echo "    macOS:  brew install espeak-ng"
                    echo "    Linux:  sudo apt install espeak-ng"
                fi
                pip install -r requirements-kokoro.txt -q
                echo "  Kokoro ✓"
                ;;
            3|piper)
                echo "Installing Piper dependencies..."
                pip install -r requirements-piper.txt -q
                echo "  Piper ✓"
                ;;
            4|elevenlabs)
                echo "Installing ElevenLabs dependencies..."
                pip install -r requirements-elevenlabs.txt -q
                echo "  ElevenLabs ✓"
                ;;
            *)
                echo "  Skipping unknown choice: $choice"
                ;;
        esac
    done
fi

# --- Make webapp scripts executable ---
echo ""
echo "Setting permissions..."
chmod +x webapp/run.sh
find webapp/routes -type f -name 'GET' -o -name 'POST' -o -name 'DELETE' | while read f; do
    if head -1 "$f" | grep -q '^#!/'; then
        chmod +x "$f"
    fi
done

echo ""
echo "============================================"
echo "  Install complete!"
echo ""
echo "  To run the web app:"
echo "    source venv/bin/activate"
echo "    cd webapp && ./run.sh"
echo "    open http://localhost:8080"
echo ""
echo "  To run the CLI pipeline:"
echo "    source venv/bin/activate"
echo "    python pipeline.py <url>"
echo "============================================"
