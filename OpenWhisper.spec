# PyInstaller spec for OpenWhisper.
#
# We use a spec file (rather than pure CLI args) because we need to pull
# in dynamic modules that PyInstaller's static analysis misses:
# faster-whisper's model backends, ctranslate2 runtime libs, and the
# full pynput platform backend.

# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = [
    ("assets/icon.ico", "assets"),
    ("assets/icon.png", "assets"),
    ("openwhisper/resources/flags", "openwhisper/resources/flags"),
]
binaries = []
hiddenimports = []

for pkg in ("faster_whisper", "ctranslate2", "tokenizers", "onnxruntime", "av"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

hiddenimports += collect_submodules("pynput")
hiddenimports += collect_submodules("httpx")
hiddenimports += [
    "keyring.backends.Windows",
    "keyring.backends.Windows.WinVaultKeyring",
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
    icon="assets/icon.ico",
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
