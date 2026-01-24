# -*- mode: python ; coding: utf-8 -*-
# Build with: venv\Scripts\pyinstaller "Whisper Voice Input.spec" --noconfirm
# Or run: build.bat
#
# IMPORTANT: This spec requires Python 3.12 (onnxruntime and PyQt6 don't have wheels for 3.13+/3.14)
# The faster_whisper assets (Silero VAD model) MUST be included for voice activity detection to work.

import os

# Get the venv site-packages path relative to spec file location
spec_dir = os.path.dirname(os.path.abspath(SPEC))
venv_site_packages = os.path.join(spec_dir, 'venv', 'Lib', 'site-packages')
faster_whisper_assets = os.path.join(venv_site_packages, 'faster_whisper', 'assets')

a = Analysis(
    ['src\\main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets', 'assets'),  # Include icons and images
        (faster_whisper_assets, 'faster_whisper/assets'),  # Silero VAD model for faster-whisper
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Whisper Voice Input',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets\\Whisper-to-Text.ico',
)
