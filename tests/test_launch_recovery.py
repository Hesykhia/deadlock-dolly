"""Startup error routing: a missing Deadlock intro/preload offers the manual load.

The controller stops verified automatic startup early when the game never runs
its hideout intro (see ``_wait_dashboard_preload``). The desktop must turn that
specific failure into an explicit choice instead of a plain error dialog; every
other failure keeps the standard dialog.
"""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from dolly.controller import PreloadUnavailableError
from dolly.gui import DollyApp


class LaunchRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.app = DollyApp.__new__(DollyApp)
        self.app.closed = False
        self.app.root = object()
        self.status = SimpleNamespace(set=Mock())
        self.app.status_text = self.status
        self.app._log = Mock()
        self.app._load_replay = Mock()
        self.app._error = Mock()

    def error(self):
        return PreloadUnavailableError(
            "Deadlock never showed its hideout intro or started the map and shader preload, "
            "so Dolly stopped the automatic check. The game session is still open: load the "
            "selected replay from Startup controls to continue without preload verification.")

    def test_preload_unavailable_offers_and_runs_the_manual_load(self):
        with patch("dolly.gui.messagebox.askyesno", return_value=True) as ask:
            self.app._report_operation_error("Starting replay editor", self.error())
        ask.assert_called_once()
        self.app._load_replay.assert_called_once()
        self.app._error.assert_not_called()
        self.assertIn("never showed its hideout intro", self.status.set.call_args[0][0])

    def test_declining_the_offer_leaves_the_replay_unloaded(self):
        with patch("dolly.gui.messagebox.askyesno", return_value=False) as ask:
            self.app._report_operation_error("Starting replay editor", self.error())
        ask.assert_called_once()
        self.app._load_replay.assert_not_called()
        self.app._error.assert_not_called()

    def test_other_startup_errors_keep_the_standard_dialog(self):
        failure = RuntimeError("The game console connection failed.")
        self.app._report_operation_error("Starting replay editor", failure)
        self.app._error.assert_called_once_with("Starting replay editor", failure)
        self.app._load_replay.assert_not_called()

    def test_closed_window_falls_back_to_the_standard_error(self):
        self.app.closed = True
        failure = self.error()
        self.app._report_operation_error("Starting replay editor", failure)
        self.app._error.assert_called_once_with("Starting replay editor", failure)
        self.app._load_replay.assert_not_called()


if __name__ == "__main__":
    unittest.main()
