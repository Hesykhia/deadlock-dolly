# Deadlock Dolly 0.6.30-alpha

High-resolution stills, a Players capture fix for the October 7 builds, and clearer
error handling.

## Highlights

- **High-resolution stills (plate + players matte + depth).** New: capture a high-resolution still of the paused view from the in-game panel or the desktop Export tab. It records the color plate, a players-only matte and a depth pass. The capture resolution ceiling is raised to 8K.
- **Players capture works on the October 7 builds.** *Before:* the reviewed scene-system vtable was pinned to the wrong address on 6757/6759 (and the 6762/6763 hotfixes), so a Players capture could not resolve the scene. *After:* the CSceneSystem vtable is corrected (`0x61e860 -> 0x61e800`) and Players capture resolves.
- **Clearer message when a camera is captured before the shot start.** *Before:* capturing a view with the replay positioned before the shot's start failed with "Camera keyframes timestamps must be nonnegative". *After:* Dolly explains the replay is before the shot's start and how to fix it.
- **The held health panel is surfaced.** *Before:* when the health/ability panel could not be restored after Stop, no prompt appeared. *After:* Dolly shows the "Restore the game health panel" guidance for every camera backend.

## Changes

- Added the reviewed screenshot tool (`dolly/screenshot.py`, `dolly/screenshot_ui.py`) with the in-game "Screenshot (hero + plate)" action.
- Raised the capture resolution ceiling from 3840x2160 to 8192x8192 across the player layer, matte capture, depth sequence and video; the video capture memory cap moved from 256 MB to 2048 MB.
- Corrected `native/profiles/scenesystem-2026-10-06-6757.json` (CSceneSystem primary vtable) and regenerated the compatibility outputs.
- Surfaced the held health panel for every camera backend (`dolly/gui.py`).
- Refused an in-game camera captured before the shot start with a clear message.
- Internal: split the controller export/timing and layer-modes domains into their own modules and rebuilt the native helper. No user-visible change.

## Validation

Offline: 1,914 Python tests pass with 22 skipped; the native build and packaged portable-editor self-test pass. Live (build 6763): a bounded startup/F8/F9 smoke and a 30-frame Players capture both passed with clean exit and exact config restoration.

## Preserved behavior and limits

All camera, timeline, framing-guide, spline, Follow, Bone Picker, Native/Citadel DOF, graphics-profile and export features remain. The screenshot tool is new and not yet visually certified; Players appearance limits are unchanged.

## Updating

Extract the new Windows ZIP into a fresh folder and run Dolly.exe. Python and Tcl/Tk are bundled. Keep the previous installation until your normal workflow is checked. The Source ZIP contains the complete source manifest for this version.
