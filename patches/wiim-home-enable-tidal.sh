#!/usr/bin/env bash
set -euo pipefail

echo "========================================"
echo " WiiM Home - TIDAL Startup Patch"
echo "========================================"
echo

if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: Python 3 is required."
    exit 1
fi

python3 - <<'PY'
from pathlib import Path
import shutil
import sys

root = Path.home() / ".local/share/wha-linux"

if not root.exists():
    sys.exit(
        "ERROR: WiiM Home installation not found.\n"
        "Install the RPM and complete the DMG conversion first."
    )

candidates = sorted(
    root.glob("*/ */out/WiiM-Home-Linux/bootstrap.py".replace(" ", ""))
)

if not candidates:
    sys.exit(
        "ERROR: bootstrap.py not found.\n"
        "Run the WiiM Home converter before applying this patch."
    )

marker = "# WIIM_TIDAL_AUTOOPEN_PATCH"

patch = '''
# WIIM_TIDAL_AUTOOPEN_PATCH
# Automatically open TIDAL after WiiM Home starts.
from PySide6.QtCore import QTimer

_original_start = WiiMHome.LPStreamServiceMainWindow.start

def _start_with_tidal(self, *args, **kwargs):
    result = _original_start(self, *args, **kwargs)

    def _open_tidal():
        try:
            self.streamServiceSelectMethod("Tidal")
            print("WiiM Home: Opened TIDAL automatically")
        except Exception as error:
            print("WiiM Home: TIDAL startup failed:", error)

    QTimer.singleShot(2500, _open_tidal)
    return result

WiiMHome.LPStreamServiceMainWindow.start = _start_with_tidal

'''

insertion = "install_window_exit_patch()\n"
patched = 0
already = 0

for path in candidates:
    source = path.read_text(encoding="utf-8")

    if marker in source:
        print(f"Already patched: {path}")
        already += 1
        continue

    if insertion not in source:
        print(f"SKIPPED: Unsupported launcher structure: {path}")
        continue

    if "WiiMHome.LPStreamServiceMainWindow" not in source:
        print(f"SKIPPED: Main window class not found: {path}")
        continue

    updated = source.replace(insertion, insertion + patch, 1)

    try:
        compile(updated, str(path), "exec")
    except SyntaxError as error:
        print(f"ERROR: Validation failed: {error}")
        continue

    backup = path.with_name("bootstrap.py.pre-tidal.bak")

    if not backup.exists():
        shutil.copy2(path, backup)
        print(f"Backup: {backup}")

    path.write_text(updated, encoding="utf-8")
    print(f"PATCHED: {path}")
    patched += 1

print()
print(f"Patched: {patched}")
print(f"Already patched: {already}")

if patched == 0 and already == 0:
    sys.exit("ERROR: No compatible WiiM Home installation was patched.")

print()
print("TIDAL startup is enabled.")
print("Close WiiM Home completely and relaunch it.")
PY
