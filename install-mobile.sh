#!/bin/bash
# AlpacaCode Mobile Client — Termux installer
# Usage: curl -fsSL https://api.alpacacode.dev/install-mobile.sh | bash
set -e

echo "==> Installing AlpacaCode mobile client..."

# Install deps (Termux has Python built-in)
pip install --quiet requests rich 2>/dev/null || pip install requests rich

# Download client
DEST="$HOME/.alpacacode"
mkdir -p "$DEST"
curl -fsSL https://raw.githubusercontent.com/kaljuvee/alpacacode/main/mobile_client.py -o "$DEST/mobile_client.py"

# Create wrapper in ~/bin
mkdir -p "$HOME/bin"
cat > "$HOME/bin/alpacacode" << 'WRAPPER'
#!/bin/bash
exec python "$HOME/.alpacacode/mobile_client.py" "$@"
WRAPPER
chmod +x "$HOME/bin/alpacacode"

# Ensure ~/bin is on PATH
if ! echo "$PATH" | grep -q "$HOME/bin"; then
    echo 'export PATH="$HOME/bin:$PATH"' >> "$HOME/.bashrc"
    export PATH="$HOME/bin:$PATH"
fi

echo ""
echo "==> Installed! Run:"
echo ""
echo "    alpacacode"
echo ""
echo "    # or connect to a custom server:"
echo "    alpacacode --server http://your-server:5001"
echo ""
