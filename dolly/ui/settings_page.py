"""Settings page view: explicit variables/actions, with locally owned widgets."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk

from .widgets import GAP, ScrollPage, actions, card, disclosure, field


@dataclass(frozen=True)
class SettingsState:
    game_path: tk.Variable
    replay_folder: tk.Variable
    reshade_runtime_path: tk.Variable
    reshade_status_text: tk.Variable
    show_log: tk.Variable
    auto_updates_initial: bool


@dataclass(frozen=True)
class SettingsActions:
    browse_game: Callable[..., object]
    browse_replay_folder: Callable[..., object]
    browse_reshade: Callable[..., object]
    browse_reshade_library: Callable[..., object]
    check_updates: Callable[..., object]
    configure_reshade: Callable[..., object]
    diagnostics: Callable[..., object]
    disable_reshade: Callable[..., object]
    forget_reshade: Callable[..., object]
    open_advanced_startup: Callable[..., object]
    open_launch_options: Callable[..., object]
    recover_game_config: Callable[..., object]
    save_layout_paths: Callable[..., object]
    save_update_preference: Callable[..., object]
    select_reshade_runtime: Callable[..., object]
    toggle_log: Callable[..., object]
    build_keybinds: Callable[..., object]
    show_reshade_keybinds: Callable[..., object]


class SettingsPage:
    def __init__(self, parent, state: SettingsState, commands: SettingsActions, *, root, on_error):
        page = ScrollPage(parent)
        page.pack(fill="both", expand=True)
        self.settings_page = page
        body = page.body
        ttk.Label(body, text="SETTINGS", style="Section.TLabel").pack(anchor="w", pady=(0, GAP))
        updates = card(body, "Updates")
        self.auto_updates = tk.BooleanVar(value=state.auto_updates_initial)
        self.update_status = tk.StringVar(value="Checks published Latest releases; experimental pre-releases are ignored.")
        ttk.Checkbutton(updates, style="Card.TCheckbutton", text="Download and install updates automatically when idle", variable=self.auto_updates,
                        command=commands.save_update_preference).pack(anchor="w", pady=(0, GAP))
        self.update_check_button = actions(updates, (("Check for updates", commands.check_updates),), 1)[0]
        ttk.Label(updates, textvariable=self.update_status, wraplength=700, style="CardMuted.TLabel").pack(fill="x")
        game = card(body, "Game & files")
        field(game, "Deadlock executable", state.game_path)
        actions(game, (("Browse game...", commands.browse_game),), 1)
        field(game, "Replay folder", state.replay_folder)
        actions(game, (("Browse folder...", commands.browse_replay_folder), ("Save paths", commands.save_layout_paths)), 2)
        actions(game, (("Display launch options...", commands.open_launch_options),), 1)
        from ..graphics_profiles_ui import GraphicsProfiles
        self.graphics_profiles = GraphicsProfiles(card(body, "Replay graphics profiles"), root=root, on_error=on_error)
        self.controls_disclosure = disclosure(body, "Controls & keybinds")
        self.keybinds_tab = self.controls_disclosure.body
        commands.build_keybinds(self.keybinds_tab)
        self.reshade_card = shade = card(body, "ReShade")
        self.reshade_path_entry = field(shade, "Runtime DLL", state.reshade_runtime_path)
        self.reshade_path_entry.bind(
            "<Return>", lambda _event: commands.select_reshade_runtime(state.reshade_runtime_path.get()))
        self.reshade_browse_button, self.reshade_library_button = actions(
            shade, (("Browse runtime...", commands.browse_reshade),
                    ("Browse FX library...", commands.browse_reshade_library)), 2)
        buttons = actions(shade, (("Enable ReShade", commands.configure_reshade),
                        ("Disable for this session", commands.disable_reshade), ("Forget runtime", commands.forget_reshade)))
        self.reshade_configure_button, self.reshade_disable_button, self.reshade_forget_button = buttons
        self.reshade_disable_button.configure(state="disabled")
        actions(shade, (("Menu shortcut...", commands.show_reshade_keybinds),), 1)
        ttk.Label(shade, textvariable=state.reshade_status_text, style="CardMuted.TLabel", wraplength=760).pack(fill="x")
        tools = disclosure(body, "Troubleshooting & recovery")
        actions(tools.body, (("Startup controls...", commands.open_advanced_startup),
                             ("Recover configuration...", commands.recover_game_config),
                             ("Export diagnostics", commands.diagnostics)))
        ttk.Checkbutton(tools.body, text="Show log", variable=state.show_log, command=commands.toggle_log).pack(anchor="w", pady=(0, GAP))
