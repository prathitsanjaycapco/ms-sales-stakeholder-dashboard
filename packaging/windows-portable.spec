from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_submodules


repo_root = Path.cwd()
backend = repo_root / "backend"
sys.path.insert(0, str(backend))

analysis = Analysis(
    [str(backend / "portable_launcher.py")],
    pathex=[str(backend)],
    binaries=[],
    datas=[
        (str(repo_root / "frontend" / "dist"), "frontend_dist"),
        (str(backend / "migrations"), "migrations"),
        (str(backend / "alembic.ini"), "."),
    ],
    hiddenimports=[*collect_submodules("app"), *collect_submodules("uvicorn")],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="StakeholderDashboard",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

bundle = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="StakeholderDashboard",
)
