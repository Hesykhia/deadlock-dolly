"""Behavior contracts for UI-1 shared widgets; no application or game required."""
import tkinter as tk
from tkinter import ttk
from types import SimpleNamespace
import unittest

from dolly import gui_layout as widgets


class SharedWidgetTests(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as error:
            self.skipTest(str(error))
        self.addCleanup(self.root.destroy)
        self.root.geometry('480x320')
        style = ttk.Style(self.root)
        style.configure('TFrame', background='#101010')
        style.configure('Card.TFrame', background='#202020')
        style.configure('Equivalent.TFrame', background='#202020')
        self.errors = []
        self.root.report_callback_exception = lambda *error: self.errors.append(error)

    def tearDown(self):
        if hasattr(self, 'errors'):
            self.assertEqual(self.errors, [], 'Tk callback raised an exception')

    def test_surface_style_preserves_card_name_and_background_inheritance(self):
        for style, expected in [('TFrame', 'TFrame'), ('Rounded.Card.TFrame', 'Card.TFrame'),
                                ('Equivalent.TFrame', 'Card.TFrame')]:
            with self.subTest(style=style):
                self.assertEqual(widgets.surface_style(ttk.Frame(self.root, style=style)), expected)

    def test_card_title_padding_and_pack_contract(self):
        card = widgets.card(self.root, 'Capture')
        self.assertEqual(str(card.cget('style')), 'Rounded.Card.TFrame')
        self.assertEqual(tuple(map(int, card.cget('padding'))), (14,))
        self.assertEqual(card.pack_info()['fill'], 'x')
        self.assertEqual(tuple(map(int, card.pack_info()['pady'])), (0, 14))
        label, = card.winfo_children()
        self.assertEqual(label.cget('text'), 'Capture')
        self.assertEqual(str(label.cget('style')), 'CardTitle.TLabel')

    def test_entry_shares_variable_in_both_directions_and_inherits_surface(self):
        for surface, style in [('TFrame', 'TEntry'), ('Card.TFrame', 'Card.TEntry')]:
            with self.subTest(surface=surface):
                parent = ttk.Frame(self.root, style=surface)
                value = tk.StringVar(self.root, 'before')
                entry = widgets.field(parent, 'Name', value)
                self.assertIsInstance(entry, ttk.Entry)
                self.assertEqual(str(entry.cget('style')), style)
                self.assertEqual(str(entry.cget('textvariable')), str(value))
                value.set('external')
                self.assertEqual(entry.get(), 'external')
                entry.delete(0, 'end'); entry.insert(0, 'edited')
                self.assertEqual(value.get(), 'edited')
                self.assertEqual(entry.pack_info()['fill'], 'x')
                self.assertEqual(entry.master.winfo_children()[0].cget('text'), 'Name')

    def test_readonly_combo_selection_updates_shared_variable_and_event(self):
        parent = ttk.Frame(self.root, style='Card.TFrame')
        value = tk.StringVar(self.root, '30')
        combo = widgets.field(parent, 'FPS', value, values=('30', '60'))
        self.assertIsInstance(combo, ttk.Combobox)
        self.assertEqual(str(combo.cget('state')), 'readonly')
        self.assertEqual(str(combo.cget('style')), 'Card.TCombobox')
        self.assertEqual(tuple(combo.cget('values')), ('30', '60'))
        observed = []
        combo.bind('<<ComboboxSelected>>', lambda event: observed.append(value.get()))
        combo.current(1); combo.event_generate('<<ComboboxSelected>>')
        self.assertEqual(value.get(), '60')
        self.assertEqual(observed, ['60'])
        value.set('30'); self.assertEqual(combo.current(), 0)
        self.assertIsInstance(widgets.field(parent, 'Empty', value, values=()), ttk.Combobox)

    def test_actions_keep_independent_callbacks_order_styles_and_wrapping(self):
        parent = ttk.Frame(self.root, style='Card.TFrame')
        called = []
        specs = [(str(i), lambda value=i: called.append(value)) for i in range(5)]
        specs[1] += ('Primary.TButton',)
        buttons = widgets.actions(parent, specs, columns=2)
        for i, button in enumerate(buttons):
            grid = button.grid_info()
            self.assertEqual((grid['row'], grid['column']), (i // 2, i % 2))
            self.assertEqual(grid['sticky'], 'w')
            self.assertEqual(button.cget('text'), str(i))
        self.assertEqual(str(buttons[1].cget('style')), 'Card.Primary.TButton')
        self.assertEqual(str(buttons[0].cget('style')), 'Card.TButton')
        for index in (3, 0, 4, 1, 2): buttons[index].invoke()
        self.assertEqual(called, [3, 0, 4, 1, 2])
        self.assertEqual(widgets.actions(parent, []), [])

    def test_disclosure_toggle_preserves_children_and_values_across_reopen(self):
        parent = ttk.Frame(self.root, style='Card.TFrame')
        disclosure = widgets.disclosure(parent, 'Advanced')
        value = tk.StringVar(self.root, 'preserved')
        entry = widgets.field(disclosure.body, 'Value', value)
        self.assertFalse(disclosure.opened)
        self.assertEqual(disclosure.body.winfo_manager(), '')
        self.assertEqual(str(disclosure.toggle.cget('style')), 'Disclosure.Card.TButton')
        for _ in range(2):
            disclosure.toggle.invoke()
            self.assertTrue(disclosure.opened)
            self.assertEqual(disclosure.toggle.cget('text'), 'v  Advanced')
            self.assertEqual(disclosure.body.winfo_manager(), 'pack')
            disclosure.set_open(False)
            self.assertEqual(disclosure.toggle.cget('text'), '>  Advanced')
            self.assertEqual(disclosure.body.winfo_manager(), '')
            self.assertEqual(entry.get(), 'preserved')

    def make_page(self):
        page = widgets.ScrollPage(self.root)
        page.pack(fill='both', expand=True)
        labels = []
        for index in range(60):
            label = ttk.Label(page.body, text=str(index))
            label.pack(); labels.append(label)
        self.root.update()
        return page, labels

    def test_scroll_page_resizes_content_and_reveals_late_child(self):
        page, labels = self.make_page()
        self.assertEqual(int(float(page.canvas.itemcget(page.window, 'width'))), page.canvas.winfo_width())
        self.assertEqual(tuple(map(float, page.canvas.cget('scrollregion').split())),
                         tuple(map(float, page.canvas.bbox('all'))))
        page.reveal(labels[45]); self.root.update()
        self.assertGreater(page.canvas.yview()[0], 0)
        self.assertGreaterEqual(labels[45].winfo_rooty(), page.canvas.winfo_rooty())
        self.assertLess(labels[45].winfo_rooty(), page.canvas.winfo_rooty()+page.canvas.winfo_height())

    def test_wheel_routes_descendant_events_and_excludes_text_tree_and_other_pages(self):
        page, labels = self.make_page()
        labels[0].event_generate('<MouseWheel>', delta=-120); self.root.update()
        self.assertGreater(page.canvas.yview()[0], 0)
        before = page.canvas.yview()
        for target in (ttk.Treeview(page.body), tk.Text(page.body), ttk.Frame(self.root)):
            self.assertIsNone(page._wheel(SimpleNamespace(widget=target, delta=-120)))
            self.assertEqual(page.canvas.yview(), before)
        self.assertEqual(page._wheel(SimpleNamespace(widget=labels[0], delta=120)), 'break')
        self.assertLess(page.canvas.yview()[0], before[0])
        before = page.canvas.yview()
        page.scroll_page_wheel(SimpleNamespace(delta=0, num=5))
        self.assertGreater(page.canvas.yview()[0], before[0])
        page.scroll_page_wheel(SimpleNamespace(delta=0, num=4))
        self.assertEqual(page.canvas.yview(), before)

    def test_nonoverflowing_page_does_not_consume_wheel(self):
        page = widgets.ScrollPage(self.root); page.pack(fill='both', expand=True)
        label = ttk.Label(page.body, text='Short'); label.pack(); self.root.update()
        self.assertEqual(page.canvas.yview(), (0.0, 1.0))
        self.assertIsNone(page._wheel(SimpleNamespace(widget=label, delta=-120)))

    def test_destroy_removes_only_its_own_toplevel_wheel_binding(self):
        calls = []
        other = self.root.bind('<MouseWheel>', lambda event: calls.append(event.delta), add='+')
        first = widgets.ScrollPage(self.root)
        second = widgets.ScrollPage(self.root)
        first_id, second_id = first.bind_id, second.bind_id
        first.destroy()
        binding = self.root.bind('<MouseWheel>')
        self.assertNotIn(first_id, binding)
        self.assertIn(second_id, binding)
        self.assertIn(other, binding)
        self.assertEqual(self.root.tk.call('info', 'commands', first_id), '')
        self.root.update()
        self.root.event_generate('<MouseWheel>', delta=-120)
        self.assertEqual(calls, [-120])
        second.destroy()
        self.assertNotIn(second_id, self.root.bind('<MouseWheel>'))
        self.assertIn(other, self.root.bind('<MouseWheel>'))


class SharedWidgetBoundaryTests(unittest.TestCase):
    def test_original_layout_exports_are_the_same_widget_objects(self):
        from dolly.ui import widgets as shared
        for name in ('GAP', 'ScrollPage', 'Disclosure', 'surface_style',
                     'card', 'field', 'actions', 'disclosure'):
            with self.subTest(name=name):
                self.assertIs(getattr(widgets, name), getattr(shared, name))

    def test_importing_shared_widgets_does_not_load_application_or_pages(self):
        import subprocess
        import sys
        result = subprocess.run([sys.executable, '-c',
            'import sys; from dolly.ui import widgets; '
            'allowed = {"dolly", "dolly.ui", "dolly.ui.widgets", "dolly.ui_theme"}; '
            'unexpected = {name for name in sys.modules if name == "dolly" or name.startswith("dolly.")} - allowed; '
            'assert not unexpected, sorted(unexpected)'],
            capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
