"""Page contracts using Tk variables and named callbacks, without an app host."""
from dataclasses import fields
import tkinter as tk
from tkinter import ttk
import unittest
from unittest.mock import patch

from dolly.ui.library_page import LibraryActions, LibraryPage, LibraryState
from dolly.ui.settings_page import SettingsActions, SettingsPage, SettingsState
from dolly.ui.export_page import ExportActions, ExportPage, ExportState


class PageBoundaryTests(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as error:
            self.skipTest(str(error))
        self.addCleanup(self.root.destroy)
        self.root.withdraw()
        self.calls = []
        self.errors = []
        self.root.report_callback_exception = lambda *args: self.errors.append(args)

    def tearDown(self):
        if hasattr(self, 'errors'):
            self.assertEqual(self.errors, [])

    def variables(self, cls, **overrides):
        # Every dependency is declared by the page dataclass, not an app proxy.
        return cls(**{f.name: overrides[f.name] if f.name in overrides else
                      tk.StringVar(self.root, '') for f in fields(cls)})

    def callbacks(self, cls, **overrides):
        def record(name):
            return lambda *args, **kwargs: self.calls.append((name, args, kwargs))
        return cls(**{f.name: overrides.get(f.name, record(f.name)) for f in fields(cls)})

    def button(self, text):
        def walk(widget):
            for child in widget.winfo_children():
                yield child
                yield from walk(child)
        return next(w for w in walk(self.root) if isinstance(w, ttk.Button) and w.cget('text') == text)

    def test_library_owns_widgets_and_routes_named_operations_without_controller(self):
        def tree(parent, columns, labels, widths, height):
            frame = ttk.Frame(parent)
            widget = ttk.Treeview(frame, columns=columns, height=height)
            widget.pack()
            return frame, widget
        state = self.variables(LibraryState, hotkey_enabled=tk.BooleanVar(self.root, True))
        view = LibraryPage(self.root, state, self.callbacks(LibraryActions, tree=tree))
        self.assertEqual(view.selected_replay_text.get(), 'Choose a replay')
        state.demo_path.set('replays/example.dem')
        self.assertEqual(view.selected_replay_text.get(), 'example.dem')
        state.replay_search.set('example')
        view.play_replay_button.invoke()
        self.button('Stop / restore').invoke()
        self.button('Save as...').invoke()
        self.assertEqual([c[0] for c in self.calls], ['filter_replays', 'start_editing_session', 'stop_session', 'save_as'])
        self.assertEqual(str(view.cancel_startup_button.cget('state')), 'disabled')
        self.assertEqual(tuple(view.home_camera_driver_combo.cget('values')), ('Native (experimental)', 'Console (legacy)'))

    def test_settings_owns_preferences_controls_and_passes_keybind_parent_explicitly(self):
        state = self.variables(SettingsState, auto_updates_initial=True, show_log=tk.BooleanVar(self.root, False))
        with patch('dolly.graphics_profiles.load_library', return_value={'format': 1, 'selected': '', 'profiles': []}):
            view = SettingsPage(self.root, state, self.callbacks(SettingsActions), root=self.root,
                                on_error=lambda *args: self.fail(str(args)))
        self.assertEqual(self.calls, [('build_keybinds', (view.keybinds_tab,), {})])
        self.assertTrue(view.auto_updates.get())
        self.assertFalse(view.controls_disclosure.opened)
        self.button('Save paths').invoke()
        self.button('Menu shortcut...').invoke()
        self.button('Browse FX library...').invoke()
        self.assertEqual([c[0] for c in self.calls],
                         ['build_keybinds', 'save_layout_paths', 'show_reshade_keybinds', 'browse_reshade_library'])
        self.assertEqual(str(view.reshade_path_entry.cget('textvariable')), str(state.reshade_runtime_path))
        self.assertEqual(str(view.reshade_disable_button.cget('state')), 'disabled')
        self.assertFalse(hasattr(view.graphics_profiles, 'app'))

    def test_export_uses_supplied_choices_and_never_owns_recording_backend(self):
        booleans = {name: tk.BooleanVar(self.root, False) for name in
                    ('video_depth', 'video_depth_exr', 'video_fixed_step', 'video_game_audio',
                     'video_layer_effects', 'video_layer_players', 'video_layer_world', 'video_reconstructed_audio')}
        state = self.variables(ExportState, codec_choices=('Fixture encoder',), bitrate_choices=('Fixture rate',), **booleans)
        view = ExportPage(self.root, state, self.callbacks(ExportActions))
        self.assertEqual(tuple(view.video_codec_combo.cget('values')), ('Fixture encoder',))
        self.assertEqual(tuple(view.video_bitrate_combo.cget('values')), ('Fixture rate',))
        view.video_source_combo.current(1)
        view.video_source_combo.event_generate('<<ComboboxSelected>>')
        view.video_depth_checkbox.invoke()
        view.video_start_button.invoke()
        self.assertEqual([c[0] for c in self.calls], ['video_source_changed', 'depth_toggled', 'start_video_recording'])
        self.assertEqual(state.video_source.get(), 'Player POV')
        self.assertTrue(state.video_depth.get())
        self.assertEqual(str(view.video_stop_button.cget('state')), 'disabled')
        self.assertEqual(str(view.video_cancel_button.cget('state')), 'disabled')
        self.assertEqual(len(view.video_layer_checkboxes), 3)
        self.assertFalse(hasattr(view, 'video_export'))

    def test_page_modules_do_not_import_application_controller_or_export_backend(self):
        import subprocess
        import sys
        result = subprocess.run([sys.executable, '-c',
            'import sys; from dolly.ui import library_page, settings_page, export_page; '
            'forbidden={"dolly.gui", "dolly.gui_layout", "dolly.controller", "dolly.video_export", "dolly.launcher"}; '
            'assert not forbidden.intersection(sys.modules), sorted(forbidden.intersection(sys.modules))'],
            capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
