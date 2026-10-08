# Deadlock Dolly 0.6.26-alpha

A reliability release for Native Depth of Field and Dolly's error handling,
plus internal source hardening.

## Highlights

- **Citadel Depth of Field keeps working after a Native DOF problem.** *Before:* once Native DOF failed on a game install, every depth-of-field control (including Citadel DOF) was blocked and errored. *After:* only the Native DOF pass is held back, and Citadel DOF plus the rest of the editor keep working.
- **Dolly no longer freezes on a repeated error.** *Before:* a repeated failure (for example moving a DOF slider after a Native DOF error) could stack error dialogs and leave Dolly needing a hard close. *After:* Dolly shows one clear message and stays responsive.
- **The Native DOF checkerboard guard is more reliable.** *Before:* the guard depended on the exact engine wording for a failed shader compiler, so some installs could still show the magenta/black checkerboard. *After:* the guard recognizes the failure regardless of wording and leaves Native DOF off with an explanation.

## Changes

- `dolly/controller.py`: the Native DOF refusal is gated on the project actually using `r_dof_override`, so Citadel DOF and other edits are no longer blocked by a session-wide Native DOF failure.
- `dolly/controller.py`: shader-compiler failure detection matches a separator-normalized copy of the engine's reload output, so the real `vfx_dx` / `InitDynamicShaderCompileDLL` text is caught; the reload capture was also widened.
- `dolly/gui.py`: error dialogs coalesce so only one is open at a time; a burst of failures no longer stacks modal dialogs.
- Internal: broke the last literal import cycle (`media_transport` / `native_bridge`) and moved three controller domains into their own modules. No user-visible behavior change.

## Validation

Offline: 1,888 Python tests pass with 15 skipped; the native build and packaged portable-editor self-test pass during the release build. The reported checkerboard diagnostic (a game install whose shader compiler cannot load) is now refused cleanly with a single message.

## Preserved behavior and limits

All camera, timeline, framing-guide, spline, Follow, Bone Picker, Native DOF, Citadel DOF, graphics-profile and export features remain. Native DOF still cannot run on an install whose engine shader compiler will not load; Dolly holds it off, explains why, and suggests verifying the game files.

## Updating

Extract the new Windows ZIP into a fresh folder and run Dolly.exe. Python and Tcl/Tk are bundled. Keep the previous installation until your normal workflow is checked. The Source ZIP contains the complete source manifest for this version.
