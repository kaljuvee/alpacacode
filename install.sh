#!/bin/bash
set -euo pipefail

# AlpacaCode installer
# Usage: curl -fsSL https://alpacacode.com/install.sh | bash

REPO="https://github.com/kaljuvee/alpacacode.git"
INSTALL_DIR="$HOME/.alpacacode"
BIN_DIR="$HOME/.local/bin"

echo "==> AlpacaCode installer"

# Check Python version
if ! command -v python3.13 &>/dev/null; then
    if command -v python3 &>/dev/null; then
        PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.minor}")')
        if [ "$PY_VER" -lt 13 ]; then
            echo "Error: Python 3.13+ is required (found 3.$PY_VER)"
            exit 1
        fi
        PYTHON=python3
    else
        echo "Error: Python 3.13+ is required"
        exit 1
    fi
else
    PYTHON=python3.13
fi

echo "==> Using $($PYTHON --version)"

# Clone or update
if [ -d "$INSTALL_DIR" ]; then
    echo "==> Updating existing installation..."
    cd "$INSTALL_DIR" && git pull --ff-only
else
    echo "==> Cloning repository..."
    git clone "$REPO" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

# Create virtualenv
if [ ! -d ".venv" ]; then
    echo "==> Creating virtual environment..."
    $PYTHON -m venv .venv
fi

echo "==> Installing dependencies..."
.venv/bin/pip install -q -r requirements.txt

# Create .env from example if missing
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "==> Created .env from .env.example — edit with your API keys"
fi

# Symlink to PATH
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/alpacacode" << 'WRAPPER'
#!/bin/bash
cd "$HOME/.alpacacode" && .venv/bin/python alpaca_code.py "$@"
WRAPPER
chmod +x "$BIN_DIR/alpacacode"

echo ""
echo "==> AlpacaCode installed!"
echo "    Edit ~/.alpacacode/.env with your API keys, then run:"
echo "    alpacacode"
echo ""
echo "    (Make sure ~/.local/bin is in your PATH)"
