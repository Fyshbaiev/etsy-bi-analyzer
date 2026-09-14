# PyInstaller spec for Etsy BI Analyzer.
#
# Build with:
#     pyinstaller scripts/etsy_bi_analyzer.spec --noconfirm
#
# The result appears in dist/EtsyBIAnalyzer/.
#
# Notes:
# - onedir mode is used intentionally: startup is fast, and files can
#   be inspected. onefile unpacks into a temp directory on every run.
# - Several large Qt submodules are excluded because the app uses only
#   QtWidgets. This cuts the distributable size roughly in half.

from pathlib import Path

PROJECT_ROOT = Path(SPECPATH).resolve().parent
SRC = PROJECT_ROOT / "src"
ASSETS = PROJECT_ROOT / "assets"

block_cipher = None


a = Analysis(
    [str(SRC / "app" / "main.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[
        # Files read at runtime by the application.
        # Destination "src/database" mirrors the source layout so that
        # Path(__file__).parent / "schema.sql" resolves correctly inside
        # the packaged app.
        (
            str(SRC / "database" / "schema.sql"),
            "src/database",
        ),
    ],
    hiddenimports=[
        # Imported dynamically or not detected by static analysis.
        "src",
        "src.app",
        "src.app.main_window",
        "src.core",
        "src.core.paths",
        "src.database",
        "src.database.connection",
        "src.database.repositories",
        "src.database.repositories.imports_repo",
        "src.database.repositories.issues_repo",
        "src.database.repositories.order_items_repo",
        "src.database.repositories.orders_repo",
        "src.database.repositories.payments_repo",
        "src.importer",
        "src.importer.service",
        "src.importer.parsers",
        "src.importer.parsers.orders",
        "src.importer.parsers.order_items",
        "src.importer.parsers.payments",
        "src.analytics",
        "src.analytics.kpi",
        "src.analytics.reconciliation",
        "src.insights",
        "src.insights.rules",
        "src.reports",
        "src.reports.excel",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Qt submodules not used by the app.
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.QtQuick3D",
        "PySide6.QtQuickWidgets",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebEngineQuick",
        "PySide6.QtWebChannel",
        "PySide6.QtWebSockets",
        "PySide6.QtMultimedia",
        "PySide6.QtMultimediaWidgets",
        "PySide6.QtBluetooth",
        "PySide6.QtNfc",
        "PySide6.QtPositioning",
        "PySide6.QtSerialPort",
        "PySide6.QtSql",
        "PySide6.QtTest",
        "PySide6.Qt3DCore",
        "PySide6.Qt3DRender",
        "PySide6.Qt3DInput",
        "PySide6.Qt3DLogic",
        "PySide6.Qt3DAnimation",
        "PySide6.Qt3DExtras",
        "PySide6.QtCharts",
        "PySide6.QtDataVisualization",
        "PySide6.QtGraphs",
        "PySide6.QtOpenGL",
        "PySide6.QtOpenGLWidgets",
        "PySide6.QtPdf",
        "PySide6.QtPdfWidgets",
        "PySide6.QtRemoteObjects",
        "PySide6.QtScxml",
        "PySide6.QtSensors",
        "PySide6.QtSpatialAudio",
        "PySide6.QtStateMachine",
        "PySide6.QtSvg",
        "PySide6.QtSvgWidgets",
        "PySide6.QtUiTools",
        "PySide6.QtNetwork",
        "PySide6.QtHelp",
        "PySide6.QtDesigner",
        "PySide6.QtConcurrent",
        "PySide6.QtDBus",
        # Test and dev packages.
        "pytest",
        "py",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="EtsyBIAnalyzer",
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
    version=str(ASSETS / "version_info.txt"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="EtsyBIAnalyzer",
)