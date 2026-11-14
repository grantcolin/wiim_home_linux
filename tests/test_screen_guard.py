"""Test actual guard policy and async D-Bus recovery without a desktop."""
import ast
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock

source = Path(__file__).resolve().parents[1] / 'mini/wiim_tray.py'
tree = ast.parse(source.read_text())
node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == '_WiiMScreenGuard')

class GuardTests(unittest.TestCase):
    def setUp(self):
        self.clock = Mock(return_value=10)
        self.conn = Mock()
        self.calls = []
        self.conn.call.side_effect = lambda *args: self.calls.append(args)
        env = dict(_wiim_ss_time=NS(monotonic=self.clock), FX_AWAKE_MAX_IDLE_HOURS=4,
                   GLib=NS(timeout_add_seconds=Mock(return_value=1), source_remove=Mock(),
                           Variant=lambda sig, value: value, VariantType=lambda sig: sig),
                   Gio=NS(DBusSignalFlags=NS(NONE=0), DBusCallFlags=NS(NONE=0, NO_AUTO_START=1)))
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), 'exec'), env)
        self.app = NS(fullscreen_mode=True, art_effect='water', minimized=False,
                      window=Mock(), is_playing=True, raw_pixbuf=object(), tray=NS(conn=self.conn))
        self.app.window.is_active.return_value = False
        self.guard = env['_WiiMScreenGuard'](self.app)

    def finish(self, call, cookie=7, error=None):
        self.conn.call_finish.side_effect = error
        self.conn.call_finish.return_value = NS(unpack=lambda: (cookie,))
        call[-2](self.conn, object(), None)

    def test_fullscreen_without_focus_still_inhibits(self):
        self.assertTrue(self.guard.decide()[0])
        self.guard.check()
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.calls[1][0], 'org.freedesktop.PowerManagement.Inhibit')
        self.finish(self.calls[0])
        self.assertIn('screensaver', self.guard.cookies)
        self.guard.check()
        self.assertEqual(len(self.calls), 2)

    def test_failure_retries_after_backoff(self):
        self.guard.check()
        self.finish(self.calls[1], error=RuntimeError('KDE unavailable'))
        self.guard.check()
        self.assertEqual(len(self.calls), 2)
        self.clock.return_value = 26
        self.guard.check()
        self.assertEqual(len(self.calls), 3)
        self.finish(self.calls[-1])
        self.assertIn('power', self.guard.cookies)

    def test_restart_invalidates_cookie_and_reacquires(self):
        self.guard.check()
        self.finish(self.calls[0])
        self.guard.owner_changed(None,None,None,None,None,
            NS(unpack=lambda: ('org.freedesktop.ScreenSaver', ':1.1', ':1.2')),None)
        self.assertNotIn('screensaver', self.guard.cookies)
        self.guard.check()
        self.assertEqual(len(self.calls), 3)
        self.finish(self.calls[-1], cookie=22)
        self.assertEqual(self.guard.cookies['screensaver'][0], 22)

    def test_late_reply_after_exit_releases_cookie(self):
        self.guard.check()
        call=self.calls[0]
        self.app.fullscreen_mode=False
        self.guard.check()
        self.finish(call)
        self.assertFalse(self.guard.cookies)
        self.assertEqual(self.calls[-1][3], 'UnInhibit')

    def test_static_paused_hidden_and_finished_allow_screensaver(self):
        for field,value in [('art_effect','cover'),('is_playing',False),
                            ('minimized',True),('fullscreen_mode',False),
                            ('raw_pixbuf',None),('connect_stopped',True)]:
            with self.subTest(field=field):
                original=getattr(self.app,field,None)
                setattr(self.app,field,value)
                self.assertFalse(self.guard.decide()[0])
                setattr(self.app,field,original)

    def test_stale_reply_cannot_replace_new_cookie(self):
        self.guard.check()
        old=self.calls[0]
        self.guard.owner_changed(None,None,None,None,None,
            NS(unpack=lambda: ('org.freedesktop.ScreenSaver', ':1.1', ':1.2')),None)
        self.guard.check()
        self.finish(self.calls[-1],cookie=22)
        self.finish(old,cookie=11)
        self.assertEqual(self.guard.cookies['screensaver'][0],22)

if __name__ == '__main__':
    unittest.main()
