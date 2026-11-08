"""Exercise Mini's real connection methods without GTK or a network device."""
import ast
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

SOURCE = Path(__file__).resolve().parents[1] / 'mini/wiim_tray.py'
METHODS = {'start_discovery', 'discover_wiim_logic', 'apply_discovery_result',
           'poll_device_status', 'apply_status_result'}
tree = ast.parse(SOURCE.read_text())
owner = next(n for n in tree.body if isinstance(n, ast.ClassDef)
             and any(isinstance(m, ast.FunctionDef) and m.name == 'poll_device_status'
                     for m in n.body))
methods = [n for n in owner.body if isinstance(n, ast.FunctionDef) and n.name in METHODS]
module = ast.fix_missing_locations(ast.Module(body=[ast.ClassDef(
    name='Connection', bases=[], keywords=[], body=methods, decorator_list=[])], type_ignores=[]))


class ReconnectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.clock = Mock(return_value=100.0)
        self.thread = Mock()
        self.idle = Mock(side_effect=lambda fn, *args: fn(*args))
        self.env = dict(time=types.SimpleNamespace(monotonic=self.clock),
                        threading=types.SimpleNamespace(Thread=self.thread),
                        GLib=types.SimpleNamespace(idle_add=self.idle),
                        ICON_DIR=self.tmp.name, os=__import__('os'))
        exec(compile(module, str(SOURCE), 'exec'), self.env)
        self.app = self.env['Connection']()
        self.app.__dict__.update(wiim_ip='192.168.1.157', is_scanning=False,
                                 discovery_retry_at=0.0, poll_fetching=False,
                                 fail_count=0, lbl_title=Mock(), fetch_status_thread=Mock())

    def test_offline_scan_retries_until_network_returns(self):
        a = self.app
        for _ in range(4):
            a.apply_status_result(a.wiim_ip, None, None, 'network offline')
        self.assertIsNone(a.wiim_ip)
        self.assertTrue(a.is_scanning)
        a.apply_discovery_result(None)
        self.thread.reset_mock()
        for _ in range(3):
            self.assertTrue(a.poll_device_status())
        self.thread.assert_not_called()
        self.clock.return_value = 116.0
        a.poll_device_status()
        self.assertTrue(a.is_scanning)
        self.thread.assert_called_once()
        a.apply_discovery_result(None)
        self.clock.return_value = 132.0
        a.poll_device_status()
        a.apply_discovery_result('192.168.1.199')
        self.assertEqual(a.wiim_ip, '192.168.1.199')
        self.assertFalse(a.is_scanning)
        self.assertTrue(a.poll_fetching)
        self.assertEqual(a.fail_count, 0)
        self.assertEqual((Path(self.tmp.name) / 'wiim_tray_device_ip.txt').read_text(), a.wiim_ip)
        self.assertEqual(self.thread.call_args.kwargs['args'], (a.wiim_ip,))

    def test_discovery_exception_does_not_latch_scanning(self):
        self.app.is_scanning = True
        self.app.find_wiim_ip = Mock(side_effect=RuntimeError('network changed'))
        self.app.discover_wiim_logic()
        self.assertFalse(self.app.is_scanning)
        self.assertIsNone(self.app.wiim_ip)
        self.assertEqual(self.app.discovery_retry_at, 115.0)

    def test_startup_without_device_retries(self):
        self.app.wiim_ip = None
        self.assertTrue(self.app.poll_device_status())
        self.assertTrue(self.app.is_scanning)
        self.app.poll_device_status()
        self.thread.assert_called_once()

    def test_transient_errors_keep_current_address(self):
        self.app.apply_status_result(self.app.wiim_ip, None, None, 'timeout')
        self.assertEqual(self.app.wiim_ip, '192.168.1.157')
        self.thread.assert_not_called()

    def test_old_address_result_is_ignored(self):
        self.app.apply_status_result('192.168.1.9', None, None, 'timeout')
        self.assertEqual(self.app.fail_count, 0)
        self.thread.assert_not_called()

    def test_thread_start_failure_allows_retry(self):
        self.thread.return_value.start.side_effect = RuntimeError('thread unavailable')
        self.app.start_discovery()
        self.assertFalse(self.app.is_scanning)
        self.assertEqual(self.app.discovery_retry_at, 115.0)


if __name__ == '__main__':
    unittest.main()
