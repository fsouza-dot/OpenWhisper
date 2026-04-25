#!/bin/bash
# Generate assets/icon.icns from assets/icon.png using macOS sips + iconutil.
# Idempotent: if icon.icns exists and is newer than icon.png, exits early.
set -euo pipefail

cd "$(dirname "$0")/.."

PNG="assets/icon.png"
ICNS="assets/icon.icns"

if [[ ! -f "$PNG" ]]; then
    echo "make-icns: $PNG not found" >&2
    exit 1
fi

if [[ -f "$ICNS" && "$ICNS" -nt "$PNG" ]]; then
    echo "make-icns: $ICNS is up to date"
    exit 0
fi

ICONSET="assets/icon.iconset"
rm -rf "$ICONSET"
mkdir -p "$ICONSET"

sips -z 16 16     "$PNG" --out "$ICONSET/icon_16x16.png"      >/dev/null
sips -z 32 32     "$PNG" --out "$ICONSET/icon_16x16@2x.png"   >/dev/null
sips -z 32 32     "$PNG" --out "$ICONSET/icon_32x32.png"      >/dev/null
sips -z 64 64     "$PNG" --out "$ICONSET/icon_32x32@2x.png"   >/dev/null
sips -z 128 128   "$PNG" --out "$ICONSET/icon_128x128.png"    >/dev/null
sips -z 256 256   "$PNG" --out "$ICONSET/icon_128x128@2x.png" >/dev/null
sips -z 256 256   "$PNG" --out "$ICONSET/icon_256x256.png"    >/dev/null
sips -z 512 512   "$PNG" --out "$ICONSET/icon_256x256@2x.png" >/dev/null
sips -z 512 512   "$PNG" --out "$ICONSET/icon_512x512.png"    >/dev/null
sips -z 1024 1024 "$PNG" --out "$ICONSET/icon_512x512@2x.png" >/dev/null

iconutil -c icns "$ICONSET" -o "$ICNS"
rm -rf "$ICONSET"
echo "make-icns: wrote $ICNS"
