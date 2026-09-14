# Building the Windows executable

## Requirements

- Windows 10 or newer
- Python 3.12
- The project's virtual environment activated:
..venv\Scripts\Activate.ps1
- Development dependencies installed:
pip install -e ".[dev]"

## Build

From the project root:
python scripts/build.py

This will:

1. Remove any previous `build/` and `dist/` folders.
2. Run PyInstaller with `scripts/etsy_bi_analyzer.spec`.
3. Produce `dist/EtsyBIAnalyzer/EtsyBIAnalyzer.exe` and its
   supporting files.

The full output directory is roughly 60–90 MB.

## Running

Double-click `dist/EtsyBIAnalyzer/EtsyBIAnalyzer.exe`.

The application stores its data in `%APPDATA%\EtsyBIAnalyzer\`, not
next to the executable. This is intentional: the folder containing the
`.exe` may be read-only.

## Distribution

To give the application to another user, zip the entire
`dist/EtsyBIAnalyzer/` folder. The `.exe` will not run on its own
without the sibling files.

## Notes

- Antivirus software may flag the freshly built `.exe`. This is a
  known false positive with PyInstaller. Code signing is out of scope
  for the MVP.
- Onedir mode is used instead of onefile. Onedir starts faster and
  produces inspectable output. Onefile unpacks into a temp directory
  on every launch.
- `--noconfirm` suppresses the "remove existing dist?" prompt.

## Troubleshooting

**Missing Qt plugins**

If the app starts but shows no window, or crashes on startup with
a plugin message, the Qt platform plugin was not bundled. Verify
that `scripts/etsy_bi_analyzer.spec` has not been modified and that
`PySide6` is installed in the active environment.

**Wrong Python**

PyInstaller picks up the Python interpreter used to run
`scripts/build.py`. Make sure the venv is activated before running it.

**Large output**

The `excludes` list in the spec removes unused Qt submodules. If the
output is larger than expected, check that this list is still in place.