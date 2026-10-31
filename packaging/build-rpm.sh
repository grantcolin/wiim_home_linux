#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "$0")/.." && pwd)
build=$(mktemp -d)
trap 'rm -rf "$build"' EXIT
mkdir -p "$build"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS} "$root/dist"
for name in wha-linux-0.2.10.4.sh wiim-home wiim-home-setup org.wiim.home.desktop org.wiim.home.png; do
    cp "$root/source/$name" "$build/SOURCES/"
done
cp "$root/packaging/wiim-home-linux.spec" "$build/SPECS/"
rpmbuild -ba --define "_topdir $build" "$build/SPECS/wiim-home-linux.spec"
find "$build/RPMS" "$build/SRPMS" -name '*.rpm' -exec cp '{}' "$root/dist/" \;
