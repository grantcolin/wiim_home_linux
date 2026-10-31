#!/usr/bin/env python3
"""Extract an official macOS WiiM Home DMG without executing it."""
import shutil, subprocess, sys
from pathlib import Path

def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: extract_installer.py <official-dmg> <destination>")
    source, output = map(lambda value: Path(value).resolve(), sys.argv[1:])
    if not shutil.which("7z"):
        raise SystemExit("Missing 7z. On Arch/Manjaro: sudo pacman -S p7zip")
    shutil.rmtree(output, ignore_errors=True)
    output.mkdir(parents=True)
    result = subprocess.run(
        ["7z", "x", "-y", "-o" + str(output), str(source)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    apps = list(output.glob("**/WiiM Home.app/Contents/MacOS/WiiM Home"))
    if len(apps) != 1:
        raise SystemExit("Could not locate WiiM Home.app in official DMG (7z status %d)" % result.returncode)
    print(apps[0])

if __name__ == "__main__":
    main()
