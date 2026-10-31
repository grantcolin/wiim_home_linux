# Repackaging

The working binaries in `packages/` are preserved unchanged. The recipes here build new revisions from `source/`; they do not claim bit-for-bit reproduction of the original packages.

## Debian / Ubuntu

Requires `dpkg-deb` and standard shell/coreutils tools:

```bash
bash packaging/build-deb.sh
```

Output: `dist/wiim-home-linux_0.2.10.4-2_amd64.deb`. Metadata and post-install script were extracted from the supplied DEB. Adjust dependencies in `packaging/debian/control` for your distribution.

## RPM distributions

Requires `rpmbuild` (Fedora: `rpm-build`):

```bash
bash packaging/build-rpm.sh
```

Outputs binary and source RPMs in `dist/`. The spec is based on the earlier supplied packaging source, updated to package the current converter with revision 4. Dependency names may need changes for openSUSE or other RPM distributions. The retained MIT field comes from that original spec; it is not a blanket licence for WiiM Mini, artwork or proprietary WiiM software.

## Converter development / other distributions

`source/converter/` contains all 28 build-kit files extracted verbatim from the current embedded converter. `source/wha-linux-0.2.10.4.sh` is the executable wrapper used by the packages. Changes to extracted files must also be incorporated into the wrapper before building a package; the package recipes deliberately use that wrapper as their source of truth.

The `wiim-home` launcher, `wiim-home-setup` wrapper, desktop file and icon in `source/` show the installed layout. Keep distro-specific dependency mappings in your package recipe. The runtime conversion requires Linux x86_64, Python, uv, 7z and the Qt resource compiler; the official DMG is supplied separately by each user.

WiiM Mini is a separate Python GTK 3 application (`mini/wiim_tray.py`), with its assets embedded. Include Python GI/GTK/Cairo bindings and suitable OpenGL/XWayland dependencies if you create a distro package for it. The Home package recipes do not install Mini or automatically apply user-runtime patches.

## Validation

The DEB recipe was built and its output inspected in the publication workspace. Shell/Python source syntax was checked. RPM build and desktop runtime tests require the target distro; they have not been performed in this workspace.
