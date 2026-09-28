"""The desktop and in-game UI must share exactly one palette (dolly/ui_theme.py)."""
from pathlib import Path
import re
import subprocess
import sys
import unittest

from dolly import ui_theme


ROOT = Path(__file__).resolve().parents[1]


class UiThemeTests(unittest.TestCase):
    def test_tokens_are_valid_hex(self):
        self.assertTrue(ui_theme.TOKENS)
        for name, value in ui_theme.TOKENS.items():
            with self.subTest(token=name):
                self.assertRegex(name, r"^[a-z][a-z0-9_]*$")
                self.assertRegex(value, r"^#[0-9a-f]{6}$")
                ui_theme.rgb(value)

    def test_native_header_is_current(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "generate_ui_tokens.py"), "--check"],
            cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(
            result.returncode, 0,
            "native/src/dolly_ui_tokens_generated.hpp is stale; run tools/generate_ui_tokens.py\n"
            + result.stdout + result.stderr)

    def test_desktop_has_no_hardcoded_colours(self):
        for name in ("dolly/gui.py", "dolly/gui_theme.py", "dolly/gui_layout.py",
                     "dolly/curve.py", "dolly/release_launcher.py"):
            text = (ROOT / name).read_text(encoding="utf-8")
            found = re.findall(r"#[0-9a-fA-F]{6}", text)
            self.assertEqual(found, [], f"{name} must take colours from dolly/ui_theme.py: {found}")

    def test_overlay_takes_colours_from_the_generated_header(self):
        text = (ROOT / "native/src/dolly_overlay_win.cpp").read_text(encoding="utf-8")
        self.assertIn('#include "dolly_ui_tokens_generated.hpp"', text)
        found = re.findall(r"panel_color\(0x[0-9a-fA-F]", text)
        self.assertEqual(found, [], f"dolly_overlay_win.cpp has raw colours: {found}")


if __name__ == "__main__":
    unittest.main()
