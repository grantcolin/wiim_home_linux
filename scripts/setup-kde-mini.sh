#!/usr/bin/env bash
# Create a KDE application-menu launcher and enable login autostart.
set -euo pipefail
repo=$(cd -- "$(dirname -- "$0")/.." && pwd)
python3 - "$repo" <<'PY'
import ast
import os
from pathlib import Path
import shutil
import sys

home = Path.home()
repo = Path(sys.argv[1])
app = home / '.local/bin/wiim_tray.py'
source = app if app.is_file() else repo / 'mini/wiim_tray.py'
if not source.is_file():
    raise SystemExit('WiiM Mini source not found. Run this script from the complete repository.')

# Read the embedded icon without importing or starting the player.
tree = ast.parse(source.read_text(encoding='utf-8'))
svg = None
for node in tree.body:
    if isinstance(node, ast.Assign) and any(
        isinstance(target, ast.Name) and target.id == 'WIIM_SVG'
        for target in node.targets
    ):
        svg = ast.literal_eval(node.value)
        break
if not isinstance(svg, str) or '<svg' not in svg:
    raise SystemExit('Embedded WiiM icon not found; no launchers were changed.')
svg = svg.replace('fill="#000000"', 'fill="#35106D"', 1)

data = Path(os.environ.get('XDG_DATA_HOME') or home / '.local/share')
config = Path(os.environ.get('XDG_CONFIG_HOME') or home / '.config')
if not data.is_absolute() or not config.is_absolute():
    raise SystemExit('XDG_DATA_HOME and XDG_CONFIG_HOME must be absolute paths.')
icon = data / 'icons/hicolor/scalable/apps/wiim-mini.svg'
menu = data / 'applications/wiim-mini.desktop'
autostart = config / 'autostart/wiim-mini.desktop'
for path in (app, icon, menu, autostart):
    path.parent.mkdir(parents=True, exist_ok=True)
if not app.is_file():
    shutil.copy2(source, app)
    app.chmod(0o755)
    print('Installed WiiM Mini:', app)
else:
    print('Using existing WiiM Mini:', app)
icon.write_text(svg, encoding='utf-8')

def desktop_value(value):
    return str(value).replace('\\', '\\\\').replace('\n', '\\n').replace('\r', '\\r')

def exec_arg(value):
    value = str(value).replace('%', '%%')
    for char in ('\\', '"', '`', '$'):
        value = value.replace(char, '\\' + char)
    return desktop_value('"' + value + '"')

entry = (
    '[Desktop Entry]\n'
    'Type=Application\n'
    'Name=WiiM Mini\n'
    'Comment=WiiM mini player and album artwork effects\n'
    f'Exec={exec_arg(sys.executable)} {exec_arg(app)}\n'
    f'Icon={desktop_value(icon)}\n'
    'Terminal=false\n'
    'StartupNotify=false\n'
    'Categories=AudioVideo;Audio;Player;\n'
)
menu.write_text(entry, encoding='utf-8')
autostart.write_text(entry + 'Hidden=false\n', encoding='utf-8')
menu.chmod(0o644)
autostart.chmod(0o644)
print('KDE launcher:', menu)
print('Autostart enabled:', autostart)
print('Open WiiM Mini from the application menu. It will start automatically at your next login.')
PY
