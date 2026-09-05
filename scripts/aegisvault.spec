# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

ROOT = Path(SPECPATH).parent
a = Analysis(
    [str(ROOT / "src/aegisvault/main.py")], pathex=[str(ROOT / "src")],
    binaries=[], datas=[(str(ROOT / "src/aegisvault/text_limits.json"), "aegisvault")], hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=["tests", "PySide6", "PyQt6", "PyQt5", "shiboken6", "tkinter"], noarchive=False, optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [], name="AegisVault.Backend",
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=True, disable_windowed_traceback=False, argv_emulation=False,
    target_arch=None, codesign_identity=None, entitlements_file=None,
    icon=str(ROOT / "src/AegisVault.App/Assets/app_icon.ico"),
    version=str(ROOT / "build/aegisvault-version-info.txt"),
)
