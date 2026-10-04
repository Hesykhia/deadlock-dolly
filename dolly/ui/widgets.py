"""Shared Tk widgets; independent of page builders and application state."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .. import ui_theme

GAP = 14


class ScrollPage(ttk.Frame):
    """One vertical scroll region; wheel events stay within this page."""
    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, background=ui_theme.TOKENS["bg"], highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.body = ttk.Frame(self.canvas, padding=(16, 12))
        self.window = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.window, width=e.width))
        self.body.bind("<Configure>", self._resize)
        self.bind_id = self.winfo_toplevel().bind("<MouseWheel>", self._wheel, add="+")
        self.bind("<Destroy>", self._destroyed, add="+")

    def _resize(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _wheel(self, event):
        target = event.widget
        while target is not None and target is not self:
            if isinstance(target, (ttk.Treeview, tk.Text)):
                return
            target = getattr(target, "master", None)
        if target is self and self.canvas.yview() != (0.0, 1.0):
            self.scroll_page_wheel(event)
            return "break"

    def scroll_page_wheel(self, event):
        amount = -int(event.delta / 120) if event.delta else (-1 if getattr(event, "num", 0) == 4 else 1)
        self.canvas.yview_scroll(amount, "units")

    def _destroyed(self, event):
        if event.widget is self:
            self.winfo_toplevel().unbind("<MouseWheel>", self.bind_id)

    def reveal(self, widget):
        self.update_idletasks()
        y = widget.winfo_rooty() - self.body.winfo_rooty()
        self.canvas.yview_moveto(max(0, y - GAP) / max(1, self.body.winfo_height()))


def surface_style(parent):
    name = parent.cget("style") or "TFrame"
    if "Card." in name:
        return "Card.TFrame"
    background = ttk.Style(parent).lookup(name, "background")
    return "Card.TFrame" if background == ttk.Style(parent).lookup("Card.TFrame", "background") else "TFrame"


class Disclosure(ttk.Frame):
    def __init__(self, parent, title):
        frame_style = surface_style(parent)
        super().__init__(parent, style=frame_style)
        self.title = title
        self.opened = False
        self.toggle = ttk.Button(self, text=">  " + title, command=self.flip, style="Disclosure.Card.TButton" if frame_style == "Card.TFrame" else "Disclosure.TButton")
        self.toggle.pack(anchor="w")
        self.body = ttk.Frame(self, style=frame_style, padding=(0, 8, 0, 0))

    def flip(self):
        self.set_open(not self.opened)

    def set_open(self, value=True):
        self.opened = value
        self.toggle.configure(text=("v  " if value else ">  ") + self.title)
        if value:
            self.body.pack(fill="both", expand=True)
        else:
            self.body.pack_forget()


def card(parent, title):
    frame = ttk.Frame(parent, style="Rounded.Card.TFrame", padding=14)
    frame.pack(fill="x", pady=(0, GAP))
    ttk.Label(frame, text=title, style="CardTitle.TLabel").pack(anchor="w", pady=(0, GAP))
    return frame


def field(parent, label, variable, *, values=None):
    frame = ttk.Frame(parent, style=surface_style(parent))
    frame.pack(fill="x", pady=(0, GAP))
    ttk.Label(frame, text=label, style="CardMuted.TLabel" if surface_style(parent) == "Card.TFrame" else "Muted.TLabel").pack(anchor="w", pady=(0, 6))
    widget = (ttk.Combobox(frame, textvariable=variable, values=values, state="readonly",
                            style="Card.TCombobox" if surface_style(parent) == "Card.TFrame" else "TCombobox")
              if values is not None else ttk.Entry(frame, textvariable=variable,
                                                style="Card.TEntry" if surface_style(parent) == "Card.TFrame" else "TEntry"))
    widget.pack(fill="x")
    return widget


def actions(parent, specs, columns=3):
    """Bounded wrapping rows, never an unbounded horizontal pack of buttons."""
    frame = ttk.Frame(parent, style=surface_style(parent))
    frame.pack(fill="x")
    buttons = []
    for i, spec in enumerate(specs):
        label, command, *style = spec
        button_style = style[0] if style else "TButton"
        if surface_style(parent) == "Card.TFrame":
            button_style = "Card." + button_style
        b = ttk.Button(frame, text=label, command=command, style=button_style)
        b.grid(row=i // columns, column=i % columns, sticky="w", padx=(0, 10 if i % columns < columns-1 else 0), pady=(0, 10))
        frame.columnconfigure(i % columns, weight=0)
        buttons.append(b)
    return buttons


def disclosure(parent, title):
    d = Disclosure(parent, title)
    d.pack(fill="x", pady=(0, GAP))
    return d


