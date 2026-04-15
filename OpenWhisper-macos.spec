# PyInstaller spec for OpenWhisper (macOS).
#
# Build on macOS with:
#   python -m PyInstaller --noconfirm OpenWhisper-macos.spec
#
# Output: dist/OpenWhisper.app

# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules
import os

# Determine icon path - use .icns if available, fall back to .png
icon_path = "assets/icon.icns" if os.path.exists("assets/icon.icns") else "assets/icon.png"

datas = [
    ("assets/icon.png", "assets"),
    ("openwhisper/resources/flags", "openwhisper/resources/flags"),
]

# Add .icns if it exists
if os.path.exists("assets/icon.icns"):
    datas.append(("assets/icon.icns", "assets"))

binaries = []
hiddenimports = []

for pkg in ("faster_whisper", "ctranslate2", "tokenizers", "onnxruntime", "av"):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass  # Package may not be installed

hiddenimports += collect_submodules("pynput")
hiddenimports += collect_submodules("httpx")

# macOS keyring backend
hiddenimports += [
    "keyring.backends.macOS",
]

# Platform modules
hiddenimports += [
    "openwhisper.platform.macos",
    "openwhisper.platform.macos.insertion",
]

a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "PyQt5", "PyQt6"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="OpenWhisper",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="OpenWhisper",
)

# Create macOS .app bundle
app = BUNDLE(
    coll,
    name="OpenWhisper.app",
    icon=icon_path,
    bundle_identifier="com.openwhisper.app",
    info_plist={
        "CFBundleName": "OpenWhisper",
        "CFBundleDisplayName": "OpenWhisper",
        "CFBundleGetInfoString": "Local-first dictation assistant",
        "CFBundleVersion": "0.2.0",
        "CFBundleShortVersionString": "0.2.0",
        "NSHighResolutionCapable": True,
        "LSUIElement": True,  # Hide from Dock (menu bar / tray app)
        "NSMicrophoneUsageDescription": "OpenWhisper needs microphone access to transcribe your speech.",
        "NSAppleEventsUsageDescription": "OpenWhisper needs automation access for text insertion.",
    },
)
