# UI integration research — Panorama-native in-game editor

Research only, 2026-09-27. No live launches. Written against Dolly 0.5.48-alpha
(`8af09f1`) and the handoff `20260926-cravvnn-handoff.md`. Every claim is tagged
**[source]** (read from Dolly's source this session), **[handoff-live]**
(verified live by the other agent), or **[handoff-untested]** (a lead in that
document we have not confirmed).

The goal: make the in-game Dolly panel look and behave like part of Deadlock
instead of a bolted-on ImGui window, and fix the F6 keybind handoff, using
Deadlock's own Panorama UI system.

**Target (confirmed this session):** a **full Dolly in-game panel drawn in
Panorama** — the whole editor, not just chrome — because it is more fluid with
the game. The real objective is that it *looks and feels native*; inlaying into
the game's UI tree is the means, not a separate requirement. Develop and test
**locally / on a side branch only** until the feasibility hurdles are cleared;
do not push or merge to `main` while the approach is unproven. Precedent: the
`dolly-live` and `fetti` remote branches already hold experimental work that
was never merged.

## 0.0 Panorama vs "the F6 panorama viewer" (clarifying terminology)

Two different things share the name:

- **Panorama (the UI system)** — Deadlock's own UI framework. Every menu/HUD/
  popup is Panorama. Custom UI is added by mounting a compiled `.xml/.js/.css`
  layout, which renders **inside the game's UI tree** (inlaid), under any
  renderer. This is the mechanism we would use (handoff section 4).
- **The F6 "Panorama debug UI"** — a **developer inspector** for Panorama panels
  at runtime. It is itself built in Panorama but is a debug tool, not an
  authoring surface. Its only value to us is proof-of-life: the user seeing it
  mid-replay [user-observed] confirms Panorama runs and takes input during demo
  playback.

Dolly's current in-game panel is neither of these: it is **ImGui drawn over the
frame in the D3D11 Present hook** (`native/src/dolly_overlay_win.cpp`) — a true
overlay, DX11-only. Moving to Panorama is moving from overlaid to inlaid.

## 0. What the user confirmed this session

- Pressing **F6 during a replay opens Deadlock's Panorama debug UI**
  [user-observed]. This is the single most important fact: it **confirms
  Panorama renders and takes input during demo playback**, which the handoff
  could only mark [handoff-untested]. Panorama-in-replay is therefore real, not
  speculative.
- There is a **keybind handoff collision on F6** [user-observed].
- Desired outcome: a **native-looking in-game Dolly panel** and a **fix for the
  keybind handoff**; **Panorama chrome first** (stock look), then structure.

## 1. The F6 collision — exact cause [source]

Dolly's editor actions are an ordered ABI in `dolly/editor_actions.py`:

```
ACTION_ORDER = ("capture", "replace", "play_pause", "play_path", "stop", ...)
default keys =  "K",      "R",      "P",         "F5",       "F6",     ...
```

Index 4, **`stop` ("Stop / restore")**, defaults to **F6** (`editor_actions.py:14-20,85-89`).
Deadlock's developer Panorama/debug UI also opens on F6. So one F6 press:

1. opens Deadlock's Panorama debug UI, and
2. triggers Dolly's `stop` action (release camera, restore settings).

That is the "weird handoff" the user sees. Fix options (research):

- **Move Dolly's `stop` default off F6.** Cheapest and safest. F6 is only a
  default; `ACTION_ORDER`/IDs must not change (ABI), but the default key in
  `default_action_bindings` can. A good replacement is unbound-by-default or a
  non-game key; existing users keep their saved binding.
- **Note** F7 is already reserved for the console
  (`CONSOLE_KEY`/`CONSOLE_VK`, `editor_actions.py:34-35`), and the F-keys F5/F6/
  F7/F8/F9/F10 are all in play. A short audit of which function keys Deadlock's
  dev UI, the console and ReShade claim is warranted before re-defaulting.
- Long term, if Dolly moves into Panorama, the entry key should be a **stock
  MenuHint** the player's own binding shows (handoff 4.5), not a hardcoded F-key.

## 2. Why Panorama is the right direction [handoff-live + source]

From the handoff (verified live by the other agent on build 6701) and Dolly's
current state:

- The in-game panel is **ImGui via a D3D11 Present hook**
  (`native/src/dolly_overlay_win.cpp`, ~2.3k lines) [source]. It is DX11-only,
  which is why Dolly forces DX11 and warns on other renderers.
- Panorama is Deadlock's own UI, so it looks native for free, works under any
  renderer, and the engine owns cursor/focus/popups. The handoff's Hyperline HUD
  replaced an Electron overlay and proved the in-game Panorama route beats a
  separate window for focus/fullscreen/input [handoff-live].
- User-confirmed: Panorama debug UI already runs in replay.

So Panorama is not a gamble on "does it render"; it is a question of **how much
of Dolly can live there** and **how it talks to Dolly's process**.

## 3. Three-layer architecture (proposed)

Keep Dolly's existing ownership rules (handoff 7.4: one owner per state — the
editor owns the shot, the helper owns per-frame application, UI only presents).
Panorama is a **fourth presenter**, not a new source of truth.

```
Desktop Tk (library, files, settings, status)   <-- shrinks over time
   |  same project/controller
Python Controller  =  single source of truth for the shot + replay
   |  shared memory (per-frame camera/phase/effects)   |  UI-rate bridge (new)
   v                                                   v
Native helper (DWrite/DX11 hook, ImGui today)      Panorama panel (stock UI)
```

- **Per-frame data stays on shared memory.** Camera pose, phase, effect values
  must never cross Panorama (handoff 5, explicit).
- **Panorama only shows UI-rate state** (a few Hz): key list, selected key,
  timeline, export progress, mode. That is what the loopback bridge is for.
- The native helper keeps owning input interception and per-frame application;
  Panorama cannot do per-frame camera work.

## 4. Plan A — Panorama feasibility (the gating experiment)

This is experiment 1 in the handoff, now strongly supported by the F6
observation but still needing one confirmation: **can an added Panorama script
reach a place it can parent a Dolly panel to, during replay?**

Design (no launch now; for a later bounded live run under the umbrella):

1. **Find the layout that exists in replay.** The handoff says `hud_hideout.xml`
   is never released and can walk to `CitadelHud` in matches [handoff-live], but
   demo playback is [handoff-untested]. The user sees the Panorama debug UI in
   replay, so *some* Panorama root is alive. Candidate roots to check, in order:
   `hud_hideout` (persistent), any demo/spectator HUD layout in the shipped VPK,
   `base_dashboard`.
2. **Mount a probe** that overrides the chosen stock layout (handoff 4.7),
   inserts a `<scripts>` include, and logs `$.Msg` from a `Schedule`d tick plus a
   walk to `CitadelHud`.
3. **Acceptance** (handoff 7.3, boundaries in order): deployed hashes -> VPK
   mounted -> `$.Msg` visible in console during a loaded replay -> panel visible
   -> a real control changes the Dolly project -> lifecycle (seek, replay change,
   exit, relaunch).

Toolchain is real work (handoff 4.7): CS2 Workshop Tools `resourcecompiler.exe`
to compile `.xml/.js/.css`, a VPK mount, and a stock-layout override that must
be **rebuilt after every Deadlock update**. Dolly already mounts a SearchPaths
VPK (the confetti pack, `launcher.py:44`) so the mount path exists.

## 5. Plan B — Dolly <-> Panorama data bridge

Only needed once Plan A passes. The handoff's live-verified route (handoff 5):

- Python editor serves `http://127.0.0.1:<port>/dolly` (it already owns the
  session).
- A Panorama `<HTML>` panel in the startup layout loads it and uses
  **`document.title` -> `HTMLTitle` event** (downstream) and **`location.hash`**
  (upstream), chunked at <=3,072 chars, acknowledged, one snapshot not history.
- **Try `$.AsyncWebRequest` to loopback first** [handoff-untested] — if the
  sandbox allows it, the whole HTML-panel dance is unnecessary.

Security note [source]: Dolly already binds only loopback (`launcher.py` uses
`127.0.0.1` + `SO_EXCLUSIVEADDRUSE`); a bridge server must keep that property
and stay in the owned session.

## 6. Plan C — ImGui restyle (ships without Panorama)

The handoff's cheapest win (4.6) and needs no new transport: restyle the
existing ImGui panel with Deadlock's stock look.

- Palette/glyph targets [handoff-live]: key cap `#aca395`, letter `#10130d`,
  key-cap padding `4px 6px 2px 6px`, 16px bold letter; 20px uppercase label
  `#969087`; callout title 28px uppercase `#69e799`; menu hints at `opacity: .2`;
  stock classes `SecondaryButton`, `PopupButtonRow`, `h2 display silvered`.
- Dolly's ImGui style already sets a dark teal/amber palette
  (`dolly_overlay_win.cpp`, `panel_color(...)` calls) [source], so this is a
  retarget, not a rewrite. The single best change: render a **key-cap glyph**
  next to every bound action ("[F8] Dolly", "[Ctrl+Alt+K] Capture"), which the
  panel can derive from `editor_actions.ACTION_LABELS`/bindings it already has.

This is the plan to implement first — it improves the feel immediately and does
not depend on Plan A.

## 7. Plan D — structure: in-game vs desktop split

From the handoff's recommended direction (2) and Dolly's three surfaces

| Surface | Keep on desktop | Move / live in-game |
| --- | --- | --- |
| Library / Open replay / shot files | yes | — |
| Settings, keybinds, ReShade, updates, recovery | yes | — |
| Shot timeline (keys as markers, playhead, speed) | reference | **in-game, docked** |
| Selected-key inspector (arrive time, interpolation, framing) | reference | **in-game** |
| Lens / DOF editing | duplicate today | **one** in-game inspector |
| Export setup + progress | setup | progress **in-game** |
| Advanced ("Updates / s", relief, fixed-step, frozen) | — | behind one disclosure |

Vocabulary unification (Camera / Lens / Export) across `dolly/gui.py`,
`dolly_overlay_win.cpp`, README, user guide and log messages [source: they
disagree today]. Conservation of complexity: keep Dolly's automatic
intro/preload/load; do not add steps.

## 8. Recommended order

1. **Plan C (ImGui restyle) + F6 re-default + vocabulary** — no launch, no new
   transport; the immediate look-and-feel win and the handoff collision fix.
2. **Plan A (Panorama feasibility probe)** — one bounded live run under the
   umbrella; decides whether Panorama chrome is real for replay.
3. **Plan D (structure)** — move the timeline + inspector in-game.
4. **Plan B (bridge) + Panorama chrome** — stock key hint, stock popups for
   export results/errors, and (optionally) a Panorama panel.

## 8.1 Development policy — branch/local only

Per the user this session: build and test the Panorama panel **locally or on a
side branch**, and do **not** commit/push/merge to `main` until the original
humps (Plan A feasibility, the bridge, and mount/update maintenance) are cleared.
Existing remote branches `dolly-live` and `fetti` show the intended pattern:
experimental, unmerged. Andrew publishes; no tags/releases/PRs. When a Panorama
prototype is ready it should sit on its own branch (e.g. `panorama-ui`) and be
handed back as artifacts, not merged.

## 9. Open questions for the user

- Confirm the F6 fix preference: re-default Dolly's `stop` off F6 (keeps ABI,
  changes only the default), or leave F6 and fight for the Panorama debug UI to
  use another key? Re-defaulting is the low-risk choice.
- Is the Panorama debug UI something you use deliberately during editing, or is
  it incidental? If it is useful, Dolly should not steal its key at all.
- Any objection to the mount/compat cost: a stock-layout override must be
  rebuilt after every Deadlock update (handoff 4.7). If that maintenance is
  unwanted, prefer Plans C + D and skip Panorama chrome.

## 10. Boundaries / non-goals

- No live launches in this research pass. Plans A/B require one bounded,
  announced run each, under the existing safety umbrella and the new
  `dolly-live-testing` skill.
- Panorama must never become a second source of truth for the shot or camera
  (handoff 7.4); it presents and sends typed requests to the controller only.
- Per-frame camera/phase/effects stay on shared memory, never on the bridge.
- The stock-layout override carries a copy of a stock file; it must be
  regenerated after each game update and hash-checked like the confetti pack.
