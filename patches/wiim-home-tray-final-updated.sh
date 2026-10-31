#!/usr/bin/env bash
set -euo pipefail
python3 - <<'PY'
from pathlib import Path
import shutil, sys
root = Path.home() / '.local/share/wha-linux'
paths = sorted(root.glob('*/*/out/WiiM-Home-Linux/bootstrap.py'))
if not paths:
    sys.exit('ERROR: No converted WiiM Home bootstrap.py found.')
marker = '# WIIM_NATIVE_TRAY_TOGGLE_V3'
patch = '''# WIIM_NATIVE_TRAY_TOGGLE_V3
# Reuse WiiM Home's own LPTrayMenuController; never create a second tray icon.
from PySide6.QtCore import Qt as _wt_Qt
from PySide6.QtWidgets import QApplication as _wt_App, QWidget as _wt_Widget, QSystemTrayIcon as _wt_Tray
from HOME.Menu import LPTrayMenuController as _wt_tray_module

_wt_Window = WiiMHome.LPStreamServiceMainWindow
_wt_original_start = _wt_Window.start
_wt_original_setup = _wt_tray_module.LPTrayMenuController.setupTrayMenu

def _wt_hide_window(window):
    # Bypass the app's hide() override, which may initiate shutdown.
    _wt_Widget.hide(window)

def _wt_toggle_window(window):
    if window.isVisible():
        _wt_hide_window(window)
    else:
        _wt_Widget.show(window)
        window.raise_()
        window.activateWindow()

def _wt_start(self, *args, **kwargs):
    app = _wt_App.instance()
    if app:
        app.setQuitOnLastWindowClosed(False)
    # Apply before start() displays the window (Plasma Wayland taskbar hint).
    self.setWindowFlag(_wt_Qt.WindowType.Tool, True)
    return _wt_original_start(self, *args, **kwargs)

def _wt_close_event(self, event):
    event.ignore()
    _wt_hide_window(self)

def _wt_setup_tray(self, *args, **kwargs):
    result = _wt_original_setup(self, *args, **kwargs)
    tray = getattr(self, 'trayIcon', None)
    if tray is None:
        print('WiiM tray: existing tray icon not found')
        return result
    owner = getattr(self, 'owner', None)
    def get_window():
        if isinstance(owner, _wt_Window):
            return owner
        app = _wt_App.instance()
        if app:
            for window in app.topLevelWidgets():
                if isinstance(window, _wt_Window):
                    return window
        return None
    def toggle(*unused):
        window = get_window()
        if window is not None:
            _wt_toggle_window(window)
        else:
            print('WiiM tray: main window not found')
    # The original handler only responds to clicks on Windows.
    # Keep it connected (it is inert on Linux), add a Linux handler.
    def activated(reason):
        if reason == _wt_Tray.ActivationReason.Trigger:
            toggle()
    tray.activated.connect(activated)
    # Reuse original context menu. Replace only the Open action with a toggle;
    # preserve the original Quit action and its cleanup behavior.
    menu = tray.contextMenu()
    if menu is not None:
        actions = [a for a in menu.actions() if not a.isSeparator()]
        if actions:
            show_action = actions[0]
            try:
                show_action.triggered.disconnect()
            except (RuntimeError, TypeError):
                pass
            show_action.setText('Show / Hide WiiM Home')
            show_action.triggered.connect(toggle)
    # Keep Python closures alive for the lifetime of the controller.
    self._wiim_linux_tray_callbacks = (toggle, activated, get_window)
    print('WiiM tray: connected existing tray icon (no duplicate)')
    return result

# WIIM_HOME_MINI_BRIDGE_V3 - startup after the main window is ready
import os as _wb_os
import socket as _wb_socket
from PySide6.QtCore import QSocketNotifier as _wb_Notifier, QTimer as _wb_Timer
_wb_server = None
_wb_notifier = None
_wb_path = f'/tmp/wiim_home_bridge_{_wb_os.getuid()}.sock'

def _wb_accept(*unused):
    try:
        connection, _ = _wb_server.accept()
        connection.settimeout(0.3)
        try:
            command = connection.recv(32).decode('ascii', 'ignore').strip()
            app = _wt_App.instance()
            windows = [w for w in app.topLevelWidgets() if isinstance(w, _wt_Window)] if app else []
            if windows and command in ('PING', 'SHOW'):
                if command == 'SHOW':
                    window = windows[0]
                    if not window.isVisible():
                        _wt_Widget.show(window)
                    window.raise_()
                    window.activateWindow()
                connection.sendall(b'OK')
            else:
                connection.sendall(b'NO')
        finally:
            connection.close()
    except Exception as exc:
        print('WiiM bridge request error:', exc, flush=True)

def _wb_setup():
    global _wb_server, _wb_notifier
    if _wb_server is not None:
        return
    try:
        if _wb_os.path.exists(_wb_path):
            probe = _wb_socket.socket(_wb_socket.AF_UNIX, _wb_socket.SOCK_STREAM)
            try:
                probe.settimeout(0.2)
                probe.connect(_wb_path)
                print('WiiM bridge: existing listener at', _wb_path, flush=True)
                return
            except OSError:
                _wb_os.unlink(_wb_path)
            finally:
                probe.close()
        _wb_server = _wb_socket.socket(_wb_socket.AF_UNIX, _wb_socket.SOCK_STREAM)
        _wb_server.bind(_wb_path)
        _wb_os.chmod(_wb_path, 0o600)
        _wb_server.listen(4)
        _wb_server.setblocking(False)
        _wb_notifier = _wb_Notifier(_wb_server.fileno(), _wb_Notifier.Type.Read)
        _wb_notifier.activated.connect(_wb_accept)
        print('WiiM bridge READY:', _wb_path, flush=True)
    except Exception as exc:
        print('WiiM bridge startup ERROR:', exc, flush=True)

def _wb_window_start(self, *args, **kwargs):
    result = _wt_start(self, *args, **kwargs)
    # Schedule from the running main-window lifecycle, not at module import time.
    _wb_Timer.singleShot(1000, _wb_setup)
    return result

# WIIM_BRIDGE_STARTUP_FIX_V3
_wt_Window.start = _wb_window_start
_wt_Window.closeEvent = _wt_close_event
_wt_tray_module.LPTrayMenuController.setupTrayMenu = _wt_setup_tray

'''
for path in paths:
    source = path.read_text(encoding='utf-8')
    if marker in source:
        print('Already has native tray:', path, '(existing install not modified)')
        continue
    if 'from HOME import WiiMHome' not in source or 'install_window_exit_patch()' not in source:
        print('SKIPPED unsupported bootstrap:', path)
        continue
    backup = path.with_name('bootstrap.py.pre-native-tray-v3.bak')
    if not backup.exists():
        shutil.copy2(path, backup)
    # Remove the prior, unsuccessful tray patch (but not the TIDAL patch).
    old = '# WIIM_REUSE_EXISTING_TRAY_PATCH'
    if old in source:
        start = source.index(old)
        end_marker = '# WIIM_TIDAL_AUTOOPEN_PATCH'
        end = source.find(end_marker, start)
        if end == -1:
            sys.exit('ERROR: old tray patch has no TIDAL boundary; refusing to edit ' + str(path))
        source = source[:start] + source[end:]
    # Do not activate the old forced-exit-on-hide monkey patch.
    source = source.replace('\ninstall_window_exit_patch()\n', '\n# install_window_exit_patch() disabled for tray mode\n', 1)
    # Install our patch before the existing TIDAL start wrapper.
    tidal = '# WIIM_TIDAL_AUTOOPEN_PATCH'
    if tidal in source:
        source = source.replace(tidal, patch + tidal, 1)
    else:
        run_marker = '# Run main application entrypoint'
        if run_marker not in source:
            sys.exit('ERROR: cannot find insertion point in ' + str(path))
        source = source.replace(run_marker, patch + run_marker, 1)
    compile(source, str(path), 'exec')
    path.write_text(source, encoding='utf-8')
    print('PATCHED:', path)
    print('BACKUP: ', backup)
print('Fully quit and restart WiiM Home. New installs include the Mini restore bridge.')
PY
