#!/usr/bin/env bash
set -euo pipefail
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source_dmg=${WIIM_OFFICIAL_DMG:?Run ./bootstrap.sh --dmg /path/to/official.dmg}
command -v uv >/dev/null || { echo "Missing uv: install it from https://docs.astral.sh/uv/" >&2; exit 1; }
if [[ -z "${RCC:-}" ]]; then
    if command -v rcc >/dev/null 2>&1; then
        RCC="$(command -v rcc)"
    elif [[ -x /usr/lib/qt6/libexec/rcc ]]; then
        RCC="/usr/lib/qt6/libexec/rcc"
    elif [[ -x /usr/lib64/qt6/libexec/rcc ]]; then
        RCC="/usr/lib64/qt6/libexec/rcc"
    else
        echo "Missing Qt resource compiler (rcc)." >&2
        echo "On Kubuntu: sudo apt install qt6-base-dev-tools" >&2
        exit 1
    fi
fi
export RCC
command -v "$RCC" >/dev/null || { echo "Cannot execute rcc: $RCC" >&2; exit 1; }
work="$root/work"
out="$root/out/WiiM-Home-Linux"
rm -rf "$work" "$out" "$root/dist"
mkdir -p "$work" "$out/runtime"
python3 "$root/tools/extract_installer.py" "$source_dmg" "$work/extracted"
binary=$(find "$work/extracted" -path '*WiiM Home.app/Contents/MacOS/WiiM Home' -type f -print -quit)
resources=$(dirname "$(dirname "$binary")")/Resources
[[ -n $binary && -d $resources ]] || { echo "Invalid extracted official application" >&2; exit 1; }
export UV_CACHE_DIR="${UV_CACHE_DIR:-$root/.uv-cache}"
UV_PYTHON_INSTALL_DIR="$out/runtime/python" UV_PYTHON_BIN_DIR="$out/runtime/bin" uv python install 3.9.25
py39=$(find "$out/runtime/python" -type f -path '*/bin/python3.9' -print -quit)
[[ -n $py39 ]] || { echo "uv did not install Python 3.9" >&2; exit 1; }
uv run --python "$py39" --with pyinstaller python "$root/tools/unpack_pyz.py" "$binary" "$work/pyz"
uv venv --python "$py39" "$out/runtime/venv"
uv pip install --python "$out/runtime/venv/bin/python" -r "$root/requirements-linux.lock"
uv pip install --python "$out/runtime/venv/bin/python" "PySide6==6.10.3"
mkdir -p "$out/app" "$out/resources"
cp -a "$work/pyz/." "$out/app/"

# Remove incomplete macOS Qt packages so Linux PySide6 is used.
rm -rf "$out/app/PySide6" "$out/app/shiboken6"

cp -a "$resources/data" "$out/app/"
mkdir -p "$out/app/HOME"
cp -a "$resources/data" "$out/app/HOME/"
if [[ -d "$resources/Qml" ]]; then
    cp -a "$resources/Qml" "$out/app/"
else
    echo "Extracting embedded QML resources..."
    uv run --python "$py39" --with PySide6 python - "$out/app/resources" "$out/app/Qml" <<'EXTRACT_QML'
import sys
from pathlib import Path
from PySide6.QtCore import QDir, QFile, QIODevice

sys.path.insert(0, sys.argv[1])
import app_rc

destination = Path(sys.argv[2])
count = 0

def extract(directory=":/qml"):
    global count
    qdir = QDir(directory)
    flags = QDir.Filter.NoDotAndDotDot | QDir.Filter.AllEntries

    for name in qdir.entryList(flags, QDir.SortFlag.Name):
        path = directory.rstrip("/") + "/" + name
        if QDir(path).exists():
            extract(path)
        else:
            target = destination / path[len(":/qml/"):]
            target.parent.mkdir(parents=True, exist_ok=True)
            source = QFile(path)
            if not source.open(QIODevice.OpenModeFlag.ReadOnly):
                raise RuntimeError("Cannot read " + path)
            target.write_bytes(bytes(source.readAll()))
            source.close()
            count += 1

extract()
print("Extracted", count, "QML resource files")
EXTRACT_QML
fi
cp -a "$resources/images" "$out/app/"
python3 "$root/tools/apply_edits.py" "$root/patches/edits.json" "tidal-home-loading.patch" "$out/app"
python3 "$root/tools/apply_edits.py" "$root/patches/edits.json" "tidal-collection-item-count.patch" "$out/app"
# Skipped: diagnostics patch incompatible with WiiM Home 0.2.11.6
uv run --python "$out/runtime/venv/bin/python" --with PySide6 python "$root/tools/rebuild_qt_resources.py" "$out/app"
PYTHONPATH="$out/runtime/venv/lib/python3.9/site-packages:$out/app" \
  "$out/runtime/venv/bin/python" "$root/tools/verify_qrc.py" "$out/app"
cp -a "$out/app/Qml" "$out/resources/"
cp -a "$resources/images" "$out/resources/"
cp "$root/linux/bootstrap.py" "$root/linux/preset_fix.py" "$root/linux/sound_output_fix.py" "$root/linux/single_instance.py" "$root/linux/observer_lifecycle_fix.py" "$root/linux/cache_compat.py" "$root/linux/wiimradio_artwork_fallback.py" "$root/linux/app_icon.py" "$out/"
mkdir -p "$out/app/LPClientFramework/util"
cp "$root/linux/LPClientFramework/util/LPNativeCrashHandler.py" "$out/app/LPClientFramework/util/"
ln -s out "$root/dist"
cat > "$out/run.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export PYTHONPATH="$base/runtime/venv/lib/python3.9/site-packages:$base/app"
export WIIM_HOME_RESOURCES="$base/resources" WIIM_HOME_APP="$base/app"
export XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"
export BEETSDIR="${BEETSDIR:-$XDG_CONFIG_HOME/beets}"

# Plasma 6 native integration flags
export QT_QPA_PLATFORMTHEME="${QT_QPA_PLATFORMTHEME:-kde}"
export QT_WAYLAND_DISABLE_WINDOWDECORATION=0

mkdir -p "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" "$BEETSDIR"
cd "$base/app"; exec "$base/runtime/venv/bin/python" "$base/bootstrap.py" "$@"
EOF
chmod +x "$out/run.sh"
echo "Built $out"
