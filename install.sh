#!/bin/bash
# AlpacaCode — Termux installer
# Usage: curl -fsSL https://api.alpacacode.dev/install.sh | bash
set -e

echo "==> Installing AlpacaCode..."

# Install deps (Termux has Python built-in)
pip install --quiet requests rich 2>/dev/null || pip install requests rich

# Download client
DEST="$HOME/.alpacacode"
mkdir -p "$DEST"
curl -fsSL https://raw.githubusercontent.com/kaljuvee/alpacacode/main/ac.py -o "$DEST/ac.py"

# Create wrapper in ~/bin
mkdir -p "$HOME/bin"
cat > "$HOME/bin/ac" << 'WRAPPER'
#!/bin/bash
exec python "$HOME/.alpacacode/ac.py" "$@"
WRAPPER
chmod +x "$HOME/bin/ac"

# Ensure ~/bin is on PATH
if ! echo "$PATH" | grep -q "$HOME/bin"; then
    echo 'export PATH="$HOME/bin:$PATH"' >> "$HOME/.bashrc"
    export PATH="$HOME/bin:$PATH"
fi

echo ""
echo "==> Installed! Run:"
echo ""
echo "    ac"
echo ""
echo "    # or connect to a custom server:"
echo "    ac -s http://your-server:5001"
echo ""
