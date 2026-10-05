# Deadlock Dolly 0.6.17-alpha

Feature release following 0.6.16-alpha. Adds the planned editor improvements —
in-game camera editing, timeline retiming, a framing guide and spline camera
motion — plus fixes found while live-testing them.

## Highlights

- **Edit camera views in the overlay list.** *Before:* Retiming or adjusting a view meant switching back to the desktop. *After:* Edit a camera's time and bank directly in the in-game camera list, with edits streaming while you drag.
- **Drag camera ticks on the Shot timeline.** *Before:* Retiming a shot meant typing times or nudging step by step. *After:* Drag camera markers along the overlay timeline to place views exactly where you want them.
- **Framing guide on a hotkey.** *Before:* Nothing helped you check thirds or centering while composing. *After:* A clean thirds/cross grid toggles in the panel (Alt+G by default), and Escape now closes the panel like F8.
- **Spline camera motion, now the default.** *Before:* Moves could feel mechanical, and rotation channels could flatten against a key — a visible "wall". *After:* A smooth spline runs through your keys by default, in new captures and in shots saved before this update; deliberate Linear choices stay Linear.
- **ReShade FX library recovery.** *Before:* If ReShade could not find its effect folder, its menu asked you to fix it and Dolly offered no way to. *After:* Dolly registers the bundled shaders and any shader folder kept next to the selected ReShade runtime automatically, Settings → ReShade has **Browse FX library...** for anything else, and a missing library is reported instead of claiming it is ready.

## Changes

- Inline Time and Bank editing in the in-game camera table; camera-list cells are flattened and Bank edits stream while dragging.
- Draggable camera ticks on the Shot timeline with bounded drag behavior.
- Framing guide settings (version 6) with the DLYGRID1 panel block; the guide defaults off, Alt+G is the default binding, and Escape closes the panel like F8.
- Natural cubic spline interpolation (C2) with no per-segment overshoot clamp for spline; project format version 10 records an explicit Smooth/Spline choice, while version 1–9 shots stored with "smooth" now load with the spline.
- ReShade "Browse FX library..." action, automatic discovery of a shader folder beside the selected runtime, and truthful library status; the chosen or discovered folder is merged into Dolly's private ReShade configuration and applies on the next ReShade start.

## Validation

Offline: 1,891 Python tests pass with 15 skipped; the native build passes its enabled checks with the hardware-dependent encoder smoke excluded. Live: bounded replay sessions verified the framing guide and Escape behavior, the draggable ticks, the spline wall fix and default, and the ReShade library action, with the temporary deployment removed and the original configuration restored.

## Preserved behavior and limits

All existing camera, Follow, Bone Picker, graphics-profile and export features remain. Known opening-replay rendering and Players appearance limitations are unchanged, and no operating-system, driver or hardware stability fix is claimed.

## Updating

Extract the new Windows ZIP into a fresh folder and run Dolly.exe. Python and Tcl/Tk are bundled. Keep the previous installation until your normal workflow is checked. The Source ZIP contains the complete source manifest for this version.
