import unittest

from dolly.assert_watcher import choose_assert_action, dismiss_assert_dialogs


class AssertActionTests(unittest.TestCase):
    def test_rich_dialog_prefers_a_quiet_ignore(self):
        buttons = ["Launch Debugger", "Ignore", "Ignore For 24 Hours", "Ignore This File",
                   "Always Ignore", "Ignore All Asserts"]
        self.assertEqual(choose_assert_action(buttons), "Ignore For 24 Hours")

    def test_falls_back_through_the_ignore_actions(self):
        self.assertEqual(choose_assert_action(["Ignore", "Always Ignore"]), "Ignore")
        self.assertEqual(choose_assert_action(["Ignore This File"]), "Ignore This File")
        self.assertEqual(choose_assert_action(["Always Ignore"]), "Always Ignore")
        self.assertEqual(choose_assert_action(["Ignore All Asserts"]), "Ignore All Asserts")

    def test_compact_fallback_message_box_continues(self):
        self.assertEqual(choose_assert_action(["Cancel", "Try Again", "Continue"]), "Continue")
        self.assertEqual(choose_assert_action(["Cancel", "Try Again"]), "Try Again")

    def test_unknown_or_unsafe_buttons_are_never_clicked(self):
        self.assertIsNone(choose_assert_action([]))
        self.assertIsNone(choose_assert_action(["Cancel"]))
        self.assertIsNone(choose_assert_action(["Launch Debugger", "Exit Process"]))

    def test_dismiss_requires_a_windows_process_id(self):
        self.assertEqual(dismiss_assert_dialogs(0), [])
        self.assertEqual(dismiss_assert_dialogs(None), [])


if __name__ == "__main__":
    unittest.main()
