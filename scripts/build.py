"""Build the Windows executable.

Run from the project root:

    python scripts/build.py

Produces dist/EtsyBIAnalyzer/EtsyBIAnalyzer.exe and its dependencies.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPEC_FILE = PROJECT_ROOT / "scripts" / "etsy_bi_analyzer.spec"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"


def _kill_running_app() -> None:
    """Terminate any running EtsyBIAnalyzer.exe so dist/ can be removed.

    On Windows a running .exe holds a lock on its own files. Without
    this step, shutil.rmtree fails with PermissionError.
    """
    if sys.platform != "win32":
        return
    subprocess.call(
        ["taskkill", "/IM", "EtsyBIAnalyzer.exe", "/F"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _clean() -> None:
    _kill_running_app()
    for path in (DIST_DIR, BUILD_DIR):
        if not path.exists():
            continue
        print(f"Removing {path} ...")
        try:
            shutil.rmtree(path)
        except PermissionError as exc:
            print(
                f"ERROR: cannot remove {path}. "
                f"A process is still holding files there.\n"
                f"Close the running application and any Explorer or "
                f"Total Commander window pointed at that folder.\n"
                f"Original error: {exc}",
                file=sys.stderr,
            )
            raise SystemExit(1)


def _run_pyinstaller() -> int:
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(SPEC_FILE),
        "--noconfirm",
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(BUILD_DIR),
    ]
    print("Running:", " ".join(cmd))
    return subprocess.call(cmd, cwd=str(PROJECT_ROOT))


def main() -> int:
    _clean()
    rc = _run_pyinstaller()
    if rc != 0:
        print("Build failed.", file=sys.stderr)
        return rc

    exe = DIST_DIR / "EtsyBIAnalyzer" / "EtsyBIAnalyzer.exe"
    if not exe.exists():
        print(f"Expected output not found: {exe}", file=sys.stderr)
        return 1

    size_mb = sum(
        f.stat().st_size for f in exe.parent.rglob("*") if f.is_file()
    ) / (1024 * 1024)
    print()
    print(f"Build succeeded: {exe}")
    print(f"Total size: {size_mb:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())