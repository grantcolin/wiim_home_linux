"""Give the native Qt application a stable Plasma 6 identity and WiiM icon."""
import os
import shlex
import sys
from pathlib import Path


_APP_ID = "org.wiim.home"
_APP_NAME = "WiiM Home"

def icon_path(app_root=None):
    """Return the official multi-resolution WiiM icon shipped by the input."""
    root = Path(app_root or os.environ["WIIM_HOME_APP"])
    return root / "images" / "app.ico"


def desktop_entry_path(app_root=None):
    """Use KDE/XDG standard user application directory."""
    root = Path(app_root or os.environ["WIIM_HOME_APP"]).resolve()
    configured = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")).resolve()
    if configured == root.parent / "data" or root in configured.parents:
        configured = Path.home() / ".local" / "share"
    return configured / "applications" / (_APP_ID + ".desktop")


def desktop_entry_text(app_root=None):
    root = Path(app_root or os.environ["WIIM_HOME_APP"]).resolve()
    launcher = root.parent / "run.sh"
    if not launcher.is_file():
        launcher = root.parent.parent.parent / "run.sh"
    icon = root / "images" / "ico.png"
    return """[Desktop Entry]
Type=Application
Name=%s
GenericName=Audio Control Center
Comment=Control WiiM devices across your network
Exec=%s
Icon=%s
Terminal=false
Categories=AudioVideo;Audio;Player;Qt;
StartupWMClass=%s
X-KDE-Wayland-AppID=%s
StartupNotify=true
""" % (_APP_NAME, shlex.quote(str(launcher)), str(icon), _APP_ID, _APP_ID)


def ensure_desktop_entry(app_root=None):
    path = desktop_entry_path(app_root)
    content = desktop_entry_text(app_root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.read_text(encoding="utf-8") == content:
            return path
        path.write_text(content, encoding="utf-8")
        return path
    except (PermissionError, OSError) as err:
        sys.stderr.write("Warning: Could not write desktop entry: %s\n" % err)
        return path


def configure_application(application):
    """Set Plasma 6 Wayland/X11 app identity before windows map."""
    application.setApplicationName(_APP_NAME)
    if hasattr(application, "setApplicationDisplayName"):
        application.setApplicationDisplayName(_APP_NAME)
    if hasattr(application, "setDesktopFileName"):
        application.setDesktopFileName(_APP_ID)
    return ensure_desktop_entry()


def install_app_icon():
    """Install app metadata and icon before the main window becomes visible."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication
    from HOME import LPApplication as application_module
    from HOME import WiiMHome as home_module

    application_class = application_module.LPApplication
    window_class = home_module.LPStreamServiceMainWindow
    if getattr(window_class, "_linux_app_icon_installed", False):
        return
    original_setup = window_class.setupUi
    original_application_init = application_class.__init__

    def application_init(self, *args, **kwargs):
        result = original_application_init(self, *args, **kwargs)
        configure_application(self)
        return result

    def setup_ui(self, *args, **kwargs):
        result = original_setup(self, *args, **kwargs)

        # Enforce standard Plasma system window frame and titlebar decorations
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowMinMaxButtonsHint | Qt.WindowType.WindowCloseButtonHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DontCreateNativeAncestors, False)
        self.setWindowFilePath("")

        path = icon_path()
        icon = QIcon(str(path))
        if icon.isNull():
            sys.stderr.write("Warning: WiiM application icon is unavailable: %s\n" % path)
        else:
            application = QApplication.instance()
            if application is not None:
                application.setWindowIcon(icon)
            self.setWindowIcon(icon)
        return result

    application_class.__init__ = application_init
    window_class.setupUi = setup_ui
    window_class._linux_app_icon_installed = True

