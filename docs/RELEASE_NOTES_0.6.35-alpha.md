# Deadlock Dolly 0.6.35-alpha

High-resolution screenshot assembly no longer opens a console window.

## Highlights

- **High-resolution screenshot assembly no longer leaves a stuck command window.** *Before:* assembling a high-resolution still (plate extraction and alpha merge) could flash a console window that stayed open, and in the packaged app FFmpeg could load the editor's libraries. *After:* the still assembler runs FFmpeg hidden in its own clean environment, matching the Players layer encoder.

## Changes

- `dolly/screenshot.py`: the still-assembly FFmpeg now spawns with `CREATE_NO_WINDOW` and `external_program_environment()`, like the players MOV encoder, so packaged builds don't hand FFmpeg PyInstaller's DLL search path or open a console whose Close button can kill it.

## Validation

Offline: 1,919 Python tests pass with 22 skipped; the native build and the packaged portable-editor self-test pass. No live game session was needed for this change.

## Preserved behavior and limits

All camera, timeline, framing-guide, spline, Follow, Bone Picker, Native/Citadel DOF, graphics-profile, screenshot and export features remain, including the October 8 hotfix (6766) support, the health-panel restore fix and the Native DOF compiler fix. Players appearance limits are unchanged.

## Updating

Extract the new Windows ZIP into a fresh folder and run Dolly.exe. Python and Tcl/Tk are bundled. Keep the previous installation until your normal workflow is checked. The Source ZIP contains the complete source manifest for this version.
