#!/bin/bash
# Build OpenWhisper for macOS (Apple Silicon).
#
# Prerequisites:
#   - macOS 12+ on an arm64 Mac
#   - Homebrew (https://brew.sh)
#   - Python 3.11+
#
# Output:
#   dist/OpenWhisper.app
#   OpenWhisper-arm64.dmg
set -euo pipefail

cd "$(dirname "$0")"

echo "=== OpenWhisper macOS Build ==="

# 1. System deps
if ! command -v brew >/dev/null 2>&1; then
    echo "Homebrew is required. Install from https://brew.sh" >&2
    exit 1
fi
brew list portaudio &>/dev/null || brew install portaudio

# 2. Virtualenv
if [[ ! -d .venv ]]; then
    python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

# 3. Python deps
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

# 4. Icon
./scripts/make-icns.sh

# 5. PyInstaller
python -m PyInstaller --noconfirm OpenWhisper-macos.spec

# 6. Re-sign the bundle.
# PyInstaller attempts an automatic ad-hoc signature that fails on
# bundled libraries with extended attributes and leaves the bundle with
# a random per-build identifier — strip it and sign cleanly.
# If the user has run ./scripts/setup-dev-signing.sh, sign with the
# stable "OpenWhisper Dev" cert so macOS TCC's Accessibility grant
# persists across rebuilds. Otherwise fall back to ad-hoc.
xattr -cr dist/OpenWhisper.app
DEV_CERT="OpenWhisper Dev"
if security find-identity -p codesigning 2>/dev/null \
    | grep -q "\"$DEV_CERT\""
then
    echo "Signing with stable identity '$DEV_CERT' (TCC grants will persist)…"
    codesign --force --deep --sign "$DEV_CERT" \
        --identifier com.openwhisper.app dist/OpenWhisper.app
else
    echo "Signing ad-hoc (run ./scripts/setup-dev-signing.sh once for persistent TCC grants)…"
    codesign --force --deep --sign - \
        --identifier com.openwhisper.app dist/OpenWhisper.app
fi

# 7. DMG
rm -rf dmg_staging
mkdir dmg_staging
cp -R "dist/OpenWhisper.app" dmg_staging/
ln -s /Applications dmg_staging/Applications
rm -f OpenWhisper-arm64.dmg
hdiutil create \
    -volname "OpenWhisper" \
    -srcfolder dmg_staging \
    -ov -format UDZO \
    OpenWhisper-arm64.dmg
rm -rf dmg_staging

echo
echo "=== Build Complete ==="
echo "  App:  dist/OpenWhisper.app"
echo "  DMG:  OpenWhisper-arm64.dmg"
echo
echo "Install: drag the .app to /Applications, then run:"
echo "  xattr -cr /Applications/OpenWhisper.app"
