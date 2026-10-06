# Deadlock Dolly 0.6.23-alpha

Native Depth of Field safety fix following 0.6.22-alpha.

## Highlights

- **No more Native DOF checkerboard or crash when the game's vfx compiler is missing.** *Before:* enabling Native Depth of Field (`r_dof_override`) on a game install whose vfx shader compiler could not load made the engine substitute its magenta/black error material for the full-screen pass, and the corrupt pass could crash Deadlock. *After:* Dolly detects the failure before applying the pass, leaves Native DOF off for the session, and points you to Steam's file verification; Native DOF still works normally on healthy installs.

## Changes

- `Controller.ensure_native_dof_shader_support` now records the unavailability for the session instead of only warning and continuing.
- Added `Controller._require_native_dof_support`, called by shot playback, seeking, saved-camera application and the in-game/desktop DOF editor, so an authored `r_dof_override` shot never reaches the engine when its shaders cannot compile.
- The state is exposed in `status()` and diagnostics (`native_dof_unavailable`) and reset on each launch.
- Added regression tests for the blocked guard, the repeated-attempt case, projects without the override, and the in-game DOF preview path.

## Validation

Offline: 1,878 Python tests pass with 15 skipped; the native helper build and the packaged portable-editor self-test pass during the release build. The guard matches the exact engine text captured in the reported diagnostics (`InitDynamicShaderCompileDLL: Can't load vfx_dx dll, dynamic shader compile unavailable`).

Live: the failing engine text is from the affected install's own console. Confirming the refusal and the absence of the checkerboard on that install is the next in-game check.

## Preserved behavior and limits

All camera, timeline, framing-guide, spline, Follow, Bone Picker, Citadel DOF, graphics-profile and export features are unchanged. Native DOF stays unavailable on an install whose vfx shader compiler is missing until the game files are repaired; Citadel Depth of Field is unaffected.

## Updating

Extract the new Windows ZIP into a fresh folder and run Dolly.exe. Python and Tcl/Tk are bundled. Keep the previous installation until your normal workflow is checked. The Source ZIP contains the complete source manifest for this version.
