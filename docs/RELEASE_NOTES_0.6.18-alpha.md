# Deadlock Dolly 0.6.18-alpha

Maintenance release following 0.6.17-alpha. Fixes ReShade's effect library
setup so Dolly's bundled shaders load without manual configuration.

## Highlights

- **ReShade finds its shaders automatically.** *Before:* ReShade's menu could report no effect files and stay pointed at the game folder, so Dolly's bundled effects never loaded. *After:* Dolly registers the bundled shaders and any shader folder kept next to the selected runtime, so they load on the next ReShade start.
- **No more silent failure.** *Before:* Dolly could still say the shader library was ready while ReShade found nothing. *After:* it reports when no library was found, and **Browse FX library...** points at any other folder.

## Changes

- Dolly discovers `reshade-shaders`, `reshade_shaders` or `Shaders` folders beside the selected runtime DLL (or one level up) and merges them into its private ReShade configuration, alongside the bundled crosire/prod80 library.
- The chosen or discovered folder applies on the next ReShade start; the desktop status now distinguishes "library registered" from "no library found".
- Everything from 0.6.17-alpha is unchanged: in-game camera editing, draggable timeline ticks, the framing guide (Alt+G, Escape closes the panel), spline camera motion by default and the Browse FX library action.

## Validation

Offline: 1,894 Python tests pass with 15 skipped; the native build passes 26 of 26 checks; the portable bundle self-test passes (windowed GUI, unlocker hash, layouts). Package contents verified: version 0.6.18-alpha, native helper hash and the complete DeadlockDolly folder.

## Preserved behavior and limits

All camera, timeline, framing-guide, spline, Follow, Bone Picker, graphics-profile and export features remain. Known opening-replay rendering and Players appearance limitations are unchanged, and no operating-system, driver or hardware stability fix is claimed.

## Updating

Extract the new Windows ZIP into a fresh folder and run Dolly.exe. Python and Tcl/Tk are bundled. Keep the previous installation until your normal workflow is checked. The Source ZIP contains the complete source manifest for this version.
