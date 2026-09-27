---
name: dolly-live-testing
description: Use ONLY when launching Deadlock or running Dolly live replay tests, screenshots, scene-class/layer probes, seek checks, memory sampling, or any bounded in-game session. Covers the exact process-ownership, flag, camera-teleport, watchdog, cleanup and restore rules so tests are safe and repeatable.
---

# Deadlock Dolly live testing

Hard rules for driving a real Deadlock replay through the Dolly app. Follow
these so every run is bounded, safe, and leaves the machine exactly as found.

## Before any launch (preflight)

1. Announce the launch in your reply first (one explicit invocation; never a
   background relaunch loop or scheduler).
2. Confirm no game is running: `Get-Process deadlock, Dolly -ErrorAction SilentlyContinue`.
3. Confirm no leftover deployment: no `citadel_dolly_*` under
   `B:\SteamLibrary\steamapps\common\Deadlock\game\citadel`.
4. Re-hash the game modules and compare with the pinned profile in
   `native/profiles/manifest.json` (client/engine2/tier0). A game update invalidates
   Native mode and the analysis must be re-reviewed first.
5. Record the exact `gameinfo.gi` bytes/hash before touching anything; it must be
   restored byte-for-byte after.

## Ownership and flags

- Only ever control the game Dolly launched itself. Verify the owned PID via CIM
  and its command line contains **both** `-dev` and `-insecure` before any
  intervention. Never attach to an unrelated/live process.
- Dolly adds `-dev -insecure -console` (Native also `-dx11`). Keep the real
  DollyApp UI open during the run.

## The camera-teleport pitfall (important)

Seeking or stepping replay time can **snap the spectator camera back to the
spawn room**, so a screenshot shows the wrong place.

- `Controller.seek_relative` / `_seek_tick` / `step_replay_ticks` move replay
  time; they release the native camera and re-enter flight from the *saved*
  pose, but the underlying spectator can still land at spawn.
- For any test that cares WHERE the camera looks: after the seek, set the camera
  explicitly (position/angles via the camera API), wait for a settled native
  view, then capture. Do not trust the post-seek view.
- Prefer seeking to a tick where the target content (heroes, effects) is known to
  be present (mid-game ~ half the demo is dense; e.g. `107300904.dem` ≈ tick
  116000 was a team gathering in the Curiosity Shop) rather than the exact
  midpoint of the file.
- Also account for `_seek` snapping to the next recorded packet on sparse demos,
  and the tick-rate matching rules (`_replay_tick_rate_warning`).

## Scene-class / layer probes

- `sc_showclasses` lists classes as `<Name> Hide DebugLevel: 0 1 2 3`; the
  registry is **dynamic** (e.g. `projectedDecal` appears only at some ticks) —
  read it fresh each run.
- Hide = `sc_setclassflags <name> 8`; restore = `sc_setclassflags <name> 0`.
  Restore every class you hide, in a `finally`.
- Use the per-class capture harness `analysis/stability-20260925/layer_classes_probe.py`
  as the template (multi-viewpoint `--ticks`, `--confetti`).
- Note: hiding `SkinnedObject` removes hero **draws by class flag**; some hero
  passes (translucent/overlay) may not be 100% covered, so a hidden hero can
  leave faint opacity. Document this; do not claim perfect removal.
- Windows window capture: use `capture_window.ps1` (DPI-aware, ALT-tap + topmost)
  so an overlapping app is not captured. Make the game window foreground before
  capturing.

## Bounded run envelope

- Use the real DollyApp via the harness pattern in
  `analysis/stability-20260925/` (e.g. `live_memory_watch.py`,
  `paused_mem_*.py`, `layer_classes_probe.py`): one launch, a **240 s watchdog**,
  sampler on a worker thread, cleanup scheduled by the Tk thread.
- External process reads are `OpenProcess(VM_READ|QUERY)` + read-only APIs only.
  Never write game memory ad hoc.
- Snapshot config paths (gameinfo, settings, cfg/*.vcfg|cfg, video.txt) and
  restore exactly; fail loudly if gameinfo is not restored.
- Verify at the end: process exited 0, deployment removed, no remaining
  `citadel_dolly_*`, config byte-identical.

## Never ship

- Private probes/harnesses live under `analysis/` (gitignored) and never enter
  `SOURCE_FILES.txt` or a release. The private `g_pMemAlloc` allocator probe and
  all `analysis/stability-20260925/*` harnesses stay private.

## Publish policy

- Commit/push only when Andrew asks. Never publish (no tags, releases, uploads,
  PRs). Build dist locally and hand back paths + SHA-256 for Andrew to publish.
- Keep `docs/internal/ATTACH_CAMERA_PLAN.md` untouched; never commit it.
