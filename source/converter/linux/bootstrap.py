"""Native launcher compatibility flags for PyInstaller-reconstructed code."""
import argparse
import logging
import os
import runpy
import sys
import threading
import time

# Parse command line arguments (--debug switch, default OFF)
parser = argparse.ArgumentParser(description="WiiM Home Linux Native Launcher")
parser.add_argument(
    "--debug",
    action="store_true",
    default=False,
    help="Enable verbose debug logging output",
)
args, remaining_argv = parser.parse_known_args()

# Forward remaining arguments back to sys.argv
sys.argv = [sys.argv[0]] + remaining_argv

# Forcibly override all logging levels application-wide
if not args.debug:
    logging.disable(logging.INFO)
else:
    logging.disable(logging.NOTSET)
    logging.basicConfig(level=logging.DEBUG)

app = os.environ["WIIM_HOME_APP"]
from single_instance import AlreadyRunning, ObserverPortUnavailable, acquire, install_signal_cleanup, reserve_observer_port
try:
    _instance_lock = acquire()
except AlreadyRunning as error:
    print("WiiM Home: %s" % error, file=sys.stderr)
    raise SystemExit(2)
install_signal_cleanup()
try:
    reserve_observer_port()
except ObserverPortUnavailable as error:
    print("WiiM Home: %s" % error, file=sys.stderr)
    raise SystemExit(3)

# LPGlobalUI uses this flag to choose the original compiled *_ui Python
# classes instead of trying to find unbundled Qt Designer .ui files.
sys.frozen = True
sys._MEIPASS = app

from sound_output_fix import install_sound_output_fix
from cache_compat import ensure_http_cache_compatibility
from preset_fix import install_preset_fix
from observer_lifecycle_fix import install_observer_lifecycle_fix
from wiimradio_artwork_fallback import install_wiimradio_artwork_fallback
from app_icon import install_app_icon

install_preset_fix()
install_sound_output_fix()
ensure_http_cache_compatibility(os.environ["XDG_CACHE_HOME"] + "/com.linkplay.wiimhome")

import LPGlobalUI
install_observer_lifecycle_fix()
install_wiimradio_artwork_fallback()
install_app_icon()

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

def _kill():
    time.sleep(0.1)
    os.kill(os.getpid(), 9)

def _force_exit():
    try:
        from LPClientFramework import LPUPnPObserverManager
        if hasattr(LPUPnPObserverManager, "LPUPnPObserverManager"):
            manager = getattr(LPUPnPObserverManager.LPUPnPObserverManager, "instance", None)
            if manager and hasattr(manager, "stop"):
                manager.stop()
    except Exception:
        pass
    threading.Thread(target=_kill, daemon=True).start()

orig_quit = QCoreApplication.quit
QCoreApplication.quit = lambda *a, **k: (_force_exit(), orig_quit(*a, **k))

# Override WiiMHome's window close/hide logic directly
from HOME import WiiMHome

def install_window_exit_patch():
    window_class = WiiMHome.LPStreamServiceMainWindow

    orig_close_event = getattr(window_class, "closeEvent", None)
    orig_hide = getattr(window_class, "hide", None)

    def close_event(self, event):
        if orig_close_event:
            try:
                orig_close_event(self, event)
            except Exception:
                pass
        _force_exit()

    def hide(self):
        if orig_hide:
            orig_hide(self)
        _force_exit()

    window_class.closeEvent = close_event
    window_class.hide = hide

install_window_exit_patch()

# Run main application entrypoint
runpy.run_path(os.path.join(app, "main.pyc"), run_name="__main__")
