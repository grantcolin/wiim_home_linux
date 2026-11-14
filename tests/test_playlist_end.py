"""End-of-playback fullscreen policy, exercising the production method."""
import ast
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock

class PlaylistEndTests(unittest.TestCase):
    def setUp(self):
        path=Path(__file__).resolve().parents[1]/'mini/wiim_tray.py'
        tree=ast.parse(path.read_text())
        method=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef)
                    and n.name=='check_fullscreen_playback_end')
        self.clock=Mock(return_value=0)
        env={'time':NS(monotonic=self.clock),'to_int':lambda x: int(x or 0)}
        exec(compile(ast.Module(body=[method],type_ignores=[]),str(path),'exec'),env)
        self.check=env[method.name]
        self.app=NS(fullscreen_mode=True,_wiim_screen_guard=Mock(),set_fullscreen_mode=Mock())

    def poll(self,at,state='stop',position=0,duration=200000):
        self.clock.return_value=at
        self.check(self.app,state,{'curpos':position,'totlen':duration})

    def test_end_exits_and_releases(self):
        for at in (0,3,6): self.poll(at)
        self.app.set_fullscreen_mode.assert_called_once_with(False)
        self.app._wiim_screen_guard.release.assert_called_once()
        self.assertFalse(self.app._wiim_screen_guard.holding)

    def test_transition_resets_confirmation(self):
        self.poll(0);self.poll(3);self.poll(6,'play');self.poll(9)
        self.app.set_fullscreen_mode.assert_not_called()

    def test_pause_mid_track_does_not_exit(self):
        for at in (0,3,6,9): self.poll(at,'pause',100000)
        self.app.set_fullscreen_mode.assert_not_called()

    def test_pause_at_eof_exits(self):
        for at in (0,3,6): self.poll(at,'pause',200000)
        self.app.set_fullscreen_mode.assert_called_once_with(False)

    def test_fast_extra_polls_do_not_exit_early(self):
        for at in (0,.1,.2,.3): self.poll(at)
        self.app.set_fullscreen_mode.assert_not_called()

    def test_not_fullscreen_resets_confirmation(self):
        self.poll(0);self.app.fullscreen_mode=False;self.poll(3)
        self.app.fullscreen_mode=True;self.poll(6)
        self.app.set_fullscreen_mode.assert_not_called()

if __name__=='__main__': unittest.main()
