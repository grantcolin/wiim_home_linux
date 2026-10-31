#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "$0")/.." && pwd)
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
mkdir -p "$stage/DEBIAN" "$root/dist"
cp "$root/packaging/debian/"* "$stage/DEBIAN/"
# A new packaging revision distinguishes rebuilds from the supplied binary.
sed -i 's/^Version:.*/Version: 0.2.10.4-2/' "$stage/DEBIAN/control"
chmod 755 "$stage/DEBIAN/postinst"
install -Dm755 "$root/source/wiim-home" "$stage/usr/bin/wiim-home"
install -Dm755 "$root/source/wiim-home-setup" "$stage/usr/bin/wiim-home-setup"
install -Dm755 "$root/source/wha-linux-0.2.10.4.sh" "$stage/usr/share/wiim-home-linux/wha-linux-0.2.10.4.sh"
install -Dm644 "$root/source/org.wiim.home.desktop" "$stage/usr/share/applications/org.wiim.home.desktop"
install -Dm644 "$root/source/org.wiim.home.png" "$stage/usr/share/icons/hicolor/256x256/apps/org.wiim.home.png"
dpkg-deb --root-owner-group --build "$stage" "$root/dist/wiim-home-linux_0.2.10.4-2_amd64.deb"
