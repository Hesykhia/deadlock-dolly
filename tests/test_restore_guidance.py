"""Restore-guidance surfacing for a held health panel."""
from unittest.mock import Mock
import unittest

from dolly.gui import DollyApp


class RestoreGuidanceTests(unittest.TestCase):
    def app(self, *, connected, pending):
        app = DollyApp.__new__(DollyApp)
        app.controller = Mock()
        app.controller.status.return_value = {
            "connected": connected, "health_panel_restore_pending": pending}
        app.status_text = Mock()
        app._show_restore_guidance = Mock()
        app.restore_guidance_dialog = None
        return app

    def test_native_backend_pending_panel_shows_guidance(self):
        # camera_backend is "native" for every packaged Windows build; the held
        # panel must still surface (previously gated on the console backend only).
        app = self.app(connected=True, pending=True)
        app._restore_completed()
        app._show_restore_guidance.assert_called_once_with()

    def test_disconnected_pending_panel_is_surfaced_in_status(self):
        app = self.app(connected=False, pending=True)
        app._restore_completed()
        app._show_restore_guidance.assert_not_called()
        app.status_text.set.assert_called_once()
        self.assertIn("still hidden", app.status_text.set.call_args.args[0])

    def test_restored_panel_closes_open_guidance(self):
        app = self.app(connected=True, pending=False)
        dialog = Mock()
        dialog.winfo_exists.return_value = True
        app.restore_guidance_dialog = dialog
        app._restore_completed()
        dialog.destroy.assert_called_once_with()
        self.assertIsNone(app.restore_guidance_dialog)
        app._show_restore_guidance.assert_not_called()

    def test_no_guidance_when_panel_not_pending(self):
        app = self.app(connected=True, pending=False)
        app._restore_completed()
        app._show_restore_guidance.assert_not_called()


if __name__ == "__main__":
    unittest.main()
