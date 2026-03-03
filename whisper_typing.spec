# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for WhisperTyping.

Build:
    pip install pyinstaller
    pyinstaller whisper_typing.spec

Output: dist/WhisperTyping/WhisperTyping.exe
"""
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all customtkinter data files (themes, assets)
ctk_datas = collect_data_files("customtkinter")

# Collect faster-whisper data
fw_datas = collect_data_files("faster_whisper", include_py_files=False)

# Hidden imports that PyInstaller might miss
hidden_imports = [
    "sounddevice",
    "numpy",
    "faster_whisper",
    "openai",
    "customtkinter",
    "pystray",
    "PIL",
    "PIL._tkinter_finder",
    "keyboard",
    "mouse",
    "ctypes",
    "ctypes.wintypes",
    "queue",
    "wave",
    "io",
    "json",
    "pathlib",
    "dataclasses",
    "dotenv",
]
hidden_imports += collect_submodules("pystray")
hidden_imports += collect_submodules("customtkinter")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=ctk_datas + fw_datas + [
        (".env.example", "."),
    ],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "scipy", "pandas", "tkinter.test"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Filter out unnecessary files to reduce size
a.binaries = [b for b in a.binaries if not b[0].startswith("opengl")]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="WhisperTyping",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="assets/icon.ico",  # Uncomment when icon exists
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="WhisperTyping",
)
