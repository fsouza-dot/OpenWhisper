# PyInstaller spec for OpenWhisper (Linux).
#
# Build on Linux with:
#   python -m PyInstaller --noconfirm OpenWhisper-linux.spec
#
# Output: dist/OpenWhisper/OpenWhisper

# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = [("assets/icon.png", "assets")]
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

# Linux keyring backends
hiddenimports += [
    "keyring.backends.SecretService",
    "keyring.backends.kwallet",
    "secretstorage",
]

# Platform modules
hiddenimports += [
    "openwhisper.platform.linux",
    "openwhisper.platform.linux.insertion",
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
    icon="assets/icon.png",
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
