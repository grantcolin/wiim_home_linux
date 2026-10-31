Name:           wiim-home-linux
Version:        0.2.10.4
Release:        4%{?dist}
Summary:        Unofficial WiiM Home native Linux compatibility installer
License:        MIT
URL:            https://github.com/clauded/wha-linux
BuildArch:      noarch
Source0:        wha-linux-0.2.10.4.sh
Source1:        wiim-home
Source2:        wiim-home-setup
Source3:        org.wiim.home.desktop
Source4:        org.wiim.home.png
Requires:       bash
Requires:       python3
Requires:       uv
Requires:       7zip
Requires:       qt6-qtbase
Requires:       qt6-qtbase-gui
Requires:       qt6-qtwayland
Requires:       qt6-qttools

%description
Provides a launcher and upstream Linux compatibility build tooling.
The user must provide the official macOS DMG; proprietary WiiM application
assets are not redistributed. Setup builds the application in the user's
XDG data directory. First-time setup needs Internet access for Python packages.

%prep
%build
%install
install -Dm0755 %{SOURCE0} %{buildroot}%{_datadir}/wiim-home-linux/wha-linux-0.2.10.4.sh
install -Dm0755 %{SOURCE1} %{buildroot}%{_bindir}/wiim-home
install -Dm0755 %{SOURCE2} %{buildroot}%{_bindir}/wiim-home-setup
install -Dm0644 %{SOURCE3} %{buildroot}%{_datadir}/applications/org.wiim.home.desktop
install -Dm0644 %{SOURCE4} %{buildroot}%{_datadir}/icons/hicolor/256x256/apps/org.wiim.home.png

%files
%{_datadir}/wiim-home-linux/wha-linux-0.2.10.4.sh
%{_bindir}/wiim-home
%{_bindir}/wiim-home-setup
%{_datadir}/applications/org.wiim.home.desktop

%{_datadir}/icons/hicolor/256x256/apps/org.wiim.home.png
