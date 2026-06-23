# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for CxSAST Branched Projects Tree Manager.

The SDK (checkmarxpythonsdk) is installed from PyPI, so PyInstaller
finds and bundles it automatically via the normal import hooks.

Build command:
    python -m PyInstaller --clean --noconfirm cxsast-tree-manager.spec

Output: dist/CxSAST-TreeManager.exe
"""

from pathlib import Path

_here = Path(SPECPATH).absolute()
_frontend = _here.parent / "frontend"

a = Analysis(
    [str(_here / "app.py")],
    pathex=[str(_here)],
    binaries=[],
    datas=[
        (str(_frontend / "index.html"), "frontend"),
        (str(_frontend / "style.css"), "frontend"),
        (str(_frontend / "app.js"), "frontend"),
    ],
    hiddenimports=[
        "waitress",
        "CheckmarxPythonSDK",
        "CheckmarxPythonSDK.api_client",
        "CheckmarxPythonSDK.configuration",
        "CheckmarxPythonSDK.CxRestAPISDK",
        "CheckmarxPythonSDK.CxRestAPISDK.ProjectsAPI",
        "CheckmarxPythonSDK.CxRestAPISDK.TeamAPI",
        "CheckmarxPythonSDK.CxRestAPISDK.config",
        "CheckmarxPythonSDK.CxRestAPISDK.sast.projects.dto.CxProject",
        "CheckmarxPythonSDK.CxRestAPISDK.team.dto.CxTeam",
        "CheckmarxPythonSDK.utilities.compat",
        "CheckmarxPythonSDK.utilities.CxError",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "tk", "matplotlib", "numpy", "pandas", "PIL", "curses"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="CxSAST-TreeManager",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_tracked=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
