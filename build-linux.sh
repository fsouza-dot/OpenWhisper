#!/bin/bash
# Build script for OpenWhisper on Linux
#
# Prerequisites (Debian/Ubuntu):
#   sudo apt install python3-dev python3-venv portaudio19-dev \
#        libxcb-xinerama0 libxcb-cursor0 libsecret-1-dev xdotool
#
# Prerequisites (Fedora):
#   sudo dnf install python3-devel portaudio-devel libxcb libsecret-devel xdotool
#
# Prerequisites (Arch):
#   sudo pacman -S python portaudio libsecret xdotool

set -e

echo "=== OpenWhisper Linux Build ==="

# Check Python version
python3 --version || { echo "Python 3 not found"; exit 1; }

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

# Build
echo "Building OpenWhisper..."
python -m PyInstaller --noconfirm OpenWhisper-linux.spec

echo ""
echo "=== Build Complete ==="
echo "Output: dist/OpenWhisper/OpenWhisper"
echo ""
echo "To run:"
echo "  ./dist/OpenWhisper/OpenWhisper"
echo ""
echo "To create a tarball for distribution:"
echo "  cd dist && tar -czvf OpenWhisper-linux.tar.gz OpenWhisper/"
