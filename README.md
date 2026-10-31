# WiiM Home Linux & WiiM Mini

Community Linux compatibility tooling for WiiM Home, plus a standalone GTK mini player with fullscreen album-art effects. This is an unofficial project and is not affiliated with WiiM.

## Screenshots

### WiiM Home on KDE

![WiiM Home browsing favourite albums on KDE](docs/screenshots/wiim-home.png)

### Mini fullscreen vinyl

![WiiM Mini fullscreen vinyl effect with playback controls](docs/screenshots/mini-vinyl-fullscreen.png)

### Liquid effect and effect selector

![WiiM Mini liquid effect and available artwork effects](docs/screenshots/mini-liquid-menu.png)

### Escher effect

![WiiM Mini Escher effect using the album artwork](docs/screenshots/mini-escher.png)

## Included files

| Directory | Contents |
| --- | --- |
| `packages/` | Fedora RPM 0.2.10.4-3 and Debian/Ubuntu DEB 0.2.10.4-1 |
| `source/` | Launcher, setup wrapper, desktop entry and embedded converter source extracted from the supplied DEB |
| `mini/wiim_tray.py` | Latest supplied WiiM Mini source, including embedded artwork assets |
| `patches/` | TIDAL startup and native tray/Mini bridge patches |
| `packaging/` | DEB/RPM build recipes and repackaging instructions |

See [repackaging instructions](packaging/README.md) for other distributions, including extracted converter source and source-RPM generation.

The packages install compatibility tools, not the proprietary WiiM Home application. Supply your own official **macOS x86_64 DMG**. The converter checks its supported installer hashes; a different/newer DMG may require a converter update. Conversion downloads runtime dependencies.

## Install WiiM Home

Clone this repository and enter it:

```bash
git clone https://github.com/grantcolin/wiim_home_linux.git
cd wiim_home_linux
```

Fedora KDE:

```bash
sudo dnf install ./packages/wiim-home-linux-0.2.10.4-3.fc44.noarch.rpm
```

Kubuntu / Ubuntu:

```bash
sudo apt install ./packages/wiim-home-linux_0.2.10.4-1_amd64.deb
```

Install `uv` and `7z` if they are not already available, then convert your official installer **as your normal user**:

```bash
wiim-home-setup "$HOME/Downloads/WiiM Home Setup-x86_64.dmg"
```

Use the actual path to your DMG. After successful setup, close WiiM Home completely and apply the patches as the same user:

```bash
bash patches/wiim-home-enable-tidal.sh
bash patches/wiim-home-tray-final-updated.sh
wiim-home
```

The TIDAL patch opens TIDAL automatically after startup; it does not supply an account or subscription. The tray patch reuses WiiM Home's native tray icon, provides Show/Hide, keeps the app running when its window closes, and adds the local bridge used by WiiM Mini to bring Home forward. Reapply patches after rebuilding the converted app.

## Install WiiM Mini

Requires Python 3, GTK 3, PyGObject, Cairo bindings, a working OpenGL/Mesa driver, and X11/XWayland. The source requests the X11 backend for KDE window positioning. Keep the computer and WiiM device on the same local network.

From the repository directory:

```bash
mkdir -p "$HOME/.local/bin"
install -m 755 mini/wiim_tray.py "$HOME/.local/bin/wiim_tray.py"
python3 "$HOME/.local/bin/wiim_tray.py"
```

WiiM Mini includes playback controls, a volume popup, queue access, track/audio details, a deep-purple tray icon, and a fullscreen toggle. Fullscreen controls hide after 15 seconds of inactivity. Animated effects include Vinyl, Slow Zoom, Floating Sleeve, Liquid, Escher, Water and Wash; Random changes effects every two minutes. Rendering pauses while hidden in the tray.

### Start Mini automatically in KDE

```bash
mkdir -p "$HOME/.config/autostart"
cat > "$HOME/.config/autostart/wiim-mini.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=WiiM Mini
Comment=WiiM Mini player
Exec=python3 "$HOME/.local/bin/wiim_tray.py"
Terminal=false
StartupNotify=false
EOF
```

## Troubleshooting

- Launch either app from a terminal to see errors. WiiM Mini: `python3 "$HOME/.local/bin/wiim_tray.py"`.
- If Home cannot be raised from Mini, apply the included tray patch after conversion and restart Home.
- A remembered album cover does not necessarily mean a playable queue exists. Queue errors can originate on the WiiM device.
- GPU performance varies with display resolution and drivers. No minimum frame rate is guaranteed.
- These are the user's supplied working builds; syntax checks do not replace fresh installation testing on every distribution.

## Source and provenance

The initial snapshot preserves all five files from `wiim_home_linux(2).zip` byte-for-byte. They match the saved `wiim_home_linux_fix3.zip`. The extra `source/` files are extracted from the included DEB, rather than copied from an older source archive. The RPM and DEB retain their original versions and have not been rebuilt for this publication.

`SHA256SUMS` records the packaged files, patches and Mini source. No proprietary DMG or converted application runtime is included. Existing third-party notices in the tooling remain applicable; publication does not grant rights to WiiM's application or trademarks.
