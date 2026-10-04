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
                     "dolly/curve.py", "dolly/release_launcher.py", "dolly/ui/widgets.py", "dolly/ui/library_page.py",
                     "dolly/ui/settings_page.py", "dolly/ui/export_page.py"):
            text = (ROOT / name).read_text(encoding="utf-8")
            found = re.findall(r"#[0-9a-fA-F]{6}", text)
            self.assertEqual(found, [], f"{name} must take colours from dolly/ui_theme.py: {found}")

    def test_overlay_takes_colours_from_the_generated_header(self):
        text = (ROOT / "native/src/dolly_overlay_panel.cpp").read_text(encoding="utf-8")
        self.assertIn('#include "dolly_ui_tokens_generated.hpp"', text)
        found = re.findall(r"panel_color\(0x[0-9a-fA-F]", text)
        self.assertEqual(found, [], f"dolly_overlay_panel.cpp has raw colours: {found}")


class DesktopThemeInitializationTests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from dolly import gui_theme
        try:
            self.root = tk.Tk()
        except tk.TclError as error:
            self.skipTest(str(error))
        self.addCleanup(self.root.destroy)
        self.root.withdraw()
        self.errors = []
        self.root.report_callback_exception = lambda *error: self.errors.append(error)
        gui_theme.initialize(self.root)

    def tearDown(self):
        if hasattr(self, "errors"):
            self.assertEqual(self.errors, [], "Tk callback failed")

    def test_final_styles_keep_base_typography_and_rounded_overrides(self):
        from tkinter import ttk
        style = ttk.Style(self.root)
        self.assertEqual(style.theme_use(), "clam")
        self.assertEqual(self.root.cget("bg"), ui_theme.TOKENS["bg"])
        self.assertEqual(self.root.tk.splitlist(style.lookup("Title.TLabel", "font")),
                         (ui_theme.FONT_FAMILY, str(ui_theme.FONT_SIZES["title"]), "bold"))
        self.assertEqual(tuple(map(int, self.root.tk.splitlist(style.lookup("TButton", "padding")))), (10, 5))
        self.assertEqual(style.layout("TButton")[0][0], "Dolly.button")
        self.assertEqual(style.lookup("TCombobox", "fieldbackground", ("readonly",)), ui_theme.TOKENS["field"])
        self.assertEqual(style.lookup("TCombobox", "foreground", ("disabled",)), ui_theme.TOKENS["disabled_fg"])

    def test_generated_images_remain_alive_after_collection(self):
        import gc
        gc.collect()
        images = self.root._dolly_theme_images
        self.assertGreater(len(images), 0)
        live = set(self.root.tk.splitlist(self.root.tk.call("image", "names")))
        for image in images:
            self.assertIn(str(image), live)
            self.assertGreater(image.width(), 0)
            self.assertGreater(image.height(), 0)

    def test_committed_selection_clears_at_idle_without_changing_value_or_cursor(self):
        import tkinter as tk
        from tkinter import ttk
        value = tk.StringVar(self.root, "second")
        combo = ttk.Combobox(self.root, textvariable=value, values=("first", "second"), state="readonly")
        combo.selection_range(0, "end"); combo.icursor(2)
        combo.event_generate("<<ComboboxSelected>>")
        self.assertTrue(combo.selection_present())
        self.root.update_idletasks()
        self.assertFalse(combo.selection_present())
        self.assertEqual(value.get(), "second")
        self.assertEqual(combo.index("insert"), 2)
        combo.selection_range(0, "end")
        self.root.update_idletasks()
        self.assertTrue(combo.selection_present(), "Ordinary text selection must remain available")

    def test_selection_callback_tolerates_destroyed_widget(self):
        from tkinter import ttk
        combo = ttk.Combobox(self.root, values=("first",))
        combo.event_generate("<<ComboboxSelected>>")
        combo.destroy()
        self.root.update_idletasks()


if __name__ == "__main__":
    unittest.main()
