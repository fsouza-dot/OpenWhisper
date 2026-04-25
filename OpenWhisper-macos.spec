# PyInstaller spec for OpenWhisper (macOS, Apple Silicon).
#
# Build on an arm64 Mac with:
#   python -m PyInstaller --noconfirm OpenWhisper-macos.spec
#
# Output: dist/OpenWhisper.app

# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all, collect_submodules

icon_path = "assets/icon.icns" if os.path.exists("assets/icon.icns") else "assets/icon.png"

datas = [
    ("assets/icon.png", "assets"),
    ("openwhisper/resources/flags", "openwhisper/resources/flags"),
]
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
        pass

hiddenimports += collect_submodules("pynput")
hiddenimports += collect_submodules("httpx")

# PyObjC frameworks used by the macOS platform layer.
for fw in ("AppKit", "Foundation", "Quartz", "ApplicationServices"):
    try:
        hiddenimports += collect_submodules(fw)
    except Exception:
        pass

hiddenimports += [
    "keyring.backends.macOS",
    "openwhisper.platform.macos",
    "openwhisper.platform.macos.insertion",
    "openwhisper.platform.macos.cgevent",
    "openwhisper.platform.macos.accessibility",
    "openwhisper.platform.macos.startup",
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
    target_arch="arm64",
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

app = BUNDLE(
    coll,
    name="OpenWhisper.app",
    icon=icon_path,
    bundle_identifier="com.openwhisper.app",
    info_plist={
        "CFBundleName": "OpenWhisper",
        "CFBundleDisplayName": "OpenWhisper",
        "CFBundleGetInfoString": "Local-first dictation assistant",
        "CFBundleVersion": "0.3.5",
        "CFBundleShortVersionString": "0.3.5",
        "LSMinimumSystemVersion": "12.0",
        "NSHighResolutionCapable": True,
        "LSUIElement": True,  # Menu bar app: no Dock icon.
        "NSMicrophoneUsageDescription":
            "OpenWhisper needs microphone access to transcribe your speech.",
        "NSAppleEventsUsageDescription":
            "OpenWhisper needs automation access to insert transcribed text "
            "into the focused application.",
    },
)
