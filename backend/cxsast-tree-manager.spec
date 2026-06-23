# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for CxSAST Branched Projects Tree Manager.

Build command:
    pyinstaller cxsast-tree-manager.spec

Output will be in dist/CxSAST-TreeManager/
"""

import os
import sys
from pathlib import Path

_here = Path(SPECPATH).absolute()
_sdk_path = r"E:\github.com\checkmarx-python-sdk"

# Collect SDK package files so they are bundled into the executable.
# The SDK is installed in editable mode; we point directly at the source tree.
_sdk_src = Path(_sdk_path) / "CheckmarxPythonSDK"
_sdk_datas = []
for root, dirs, files in os.walk(_sdk_src):
    for f in files:
        src = Path(root) / f
        rel = src.relative_to(_sdk_src.parent)
        _sdk_datas.append((str(src), str(rel.parent)))

# Frontend static files
_frontend = _here.parent / "frontend"

a = Analysis(
    [str(_here / "app.py")],
    pathex=[str(_here), _sdk_path],
    binaries=[],
    datas=_sdk_datas + [
        (str(_frontend / "index.html"), "frontend"),
        (str(_frontend / "style.css"), "frontend"),
        (str(_frontend / "app.js"), "frontend"),
    ],
    hiddenimports=[
        "CheckmarxPythonSDK",
        "CheckmarxPythonSDK.api_client",
        "CheckmarxPythonSDK.configuration",
        "CheckmarxPythonSDK.CxRestAPISDK",
        "CheckmarxPythonSDK.CxRestAPISDK.ProjectsAPI",
        "CheckmarxPythonSDK.CxRestAPISDK.TeamAPI",
        "CheckmarxPythonSDK.CxRestAPISDK.config",
        "CheckmarxPythonSDK.CxRestAPISDK.sast",
        "CheckmarxPythonSDK.CxRestAPISDK.sast.projects",
        "CheckmarxPythonSDK.CxRestAPISDK.sast.projects.dto",
        "CheckmarxPythonSDK.CxRestAPISDK.sast.projects.dto.CxProject",
        "CheckmarxPythonSDK.CxRestAPISDK.sast.projects.dto.CxSourceSettingsLink",
        "CheckmarxPythonSDK.CxRestAPISDK.sast.projects.dto.CxLink",
        "CheckmarxPythonSDK.CxRestAPISDK.sast.projects.dto.CxProjectQueueSetting",
        "CheckmarxPythonSDK.CxRestAPISDK.sast.projects.dto.customFields",
        "CheckmarxPythonSDK.CxRestAPISDK.sast.projects.dto.customFields.CxCustomField",
        "CheckmarxPythonSDK.CxRestAPISDK.team",
        "CheckmarxPythonSDK.CxRestAPISDK.team.dto",
        "CheckmarxPythonSDK.CxRestAPISDK.team.dto.CxTeam",
        "CheckmarxPythonSDK.utilities.compat",
        "CheckmarxPythonSDK.utilities.CxError",
        "httpx",
        "httpcore",
        "h11",
        "certifi",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "tk", "matplotlib", "numpy", "pandas"],
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
