#!/bin/bash
# FreeBaby Mobile Setup Script
# Run this in Termux on your Android phone
# Usage: bash setup_termux.sh

set -e

echo "=== FreeBaby Mobile Setup ==="
echo ""

# Step 1: Update packages
echo "[1/6] Updating Termux packages..."
pkg update -y && pkg upgrade -y

# Step 2: Install system dependencies
echo "[2/6] Installing system dependencies..."
pkg install -y python git nodejs termux-api

# Step 3: Install Python packages
echo "[3/6] Installing Python packages..."
pip install requests edge-tts

# Step 4: Clone FreeBaby
echo "[4/6] Cloning FreeBaby..."
if [ -d "$HOME/FreeBaby" ]; then
    echo "  FreeBaby already exists, pulling latest..."
    cd "$HOME/FreeBaby" && git pull
else
    git clone https://github.com/weiwei0450/FreeBaby.git "$HOME/FreeBaby"
fi

# Step 5: Configure API key
echo "[5/6] Configuring API key..."
if [ ! -f "$HOME/FreeBaby/mykey.py" ]; then
    if [ -f "$HOME/FreeBaby/mykey_template.py" ]; then
        cp "$HOME/FreeBaby/mykey_template.py" "$HOME/FreeBaby/mykey.py"
        echo "  Created mykey.py from template."
        echo "  >>> EDIT ~/FreeBaby/mykey.py to add your API key! <<<"
    else
        echo "  WARNING: No mykey_template.py found. Create mykey.py manually."
    fi
else
    echo "  mykey.py already exists, skipping."
fi

# Step 6: Verify
echo "[6/6] Verifying installation..."
echo ""
echo "  Python: $(python --version 2>&1)"
echo "  Node.js: $(node --version 2>&1)"
echo "  termux-api: $(which termux-speech-to-text 2>/dev/null && echo OK || echo MISSING)"
echo "  edge-tts: $(pip show edge-tts 2>/dev/null | grep Version || echo MISSING)"
echo ""

# Check Termux:API app
if command -v termux-speech-to-text &>/dev/null; then
    echo "  [OK] Termux:API CLI available"
else
    echo "  [MISSING] Install Termux:API app from F-Droid, then run:"
    echo "           pkg install termux-api"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Install AutoX.js on your phone (https://github.com/kkevsekk1/AutoX)"
echo "  2. Open AutoX.js, enable HTTP server (port 8765)"
echo "  3. Edit ~/FreeBaby/mykey.py with your API key"
echo "  4. Run: cd ~/FreeBaby && python voice_agent.py"
echo ""
