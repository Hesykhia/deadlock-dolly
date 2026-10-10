# Deadlock Dolly 0.6.35-alpha

Every FFmpeg-based output step now runs hidden in a clean environment.

## Highlights

- **Every FFmpeg output step runs hidden in a clean environment.** *Before:* assembling a high-resolution still, encoding a Players layer, combining a layer's alpha, muxing clip audio, or encoding a depth preview could flash a console window that stayed open, and in the packaged app FFmpeg could load the editor's bundled libraries instead of its own. *After:* every FFmpeg call runs hidden with a clean environment — the same way the Players MOV encoder already did — so packaged builds no longer leak Dolly's DLL search path or open a console whose Close button can kill the encode.

## Changes

- `dolly/screenshot.py` (still assembly), `dolly/player_layer.py` (Players layer encode), `dolly/gui.py` (layer alpha combine), `dolly/clip_audio.py` (clip-audio mux) and `dolly/video_export.py` (depth preview) now launch FFmpeg with `external_program_environment()` and `CREATE_NO_WINDOW`, matching the Players MOV encoder.

## Validation

Offline: 1,921 Python tests pass with 22 skipped; the native build and the packaged portable-editor self-test pass. No live game session was needed for this change.

## Preserved behavior and limits

All camera, timeline, framing-guide, spline, Follow, Bone Picker, Native/Citadel DOF, graphics-profile, screenshot and export features remain, including the October 8 hotfix (6766) support, the health-panel restore fix and the Native DOF compiler fix. Players appearance limits are unchanged.

## Updating

Extract the new Windows ZIP into a fresh folder and run Dolly.exe. Python and Tcl/Tk are bundled. Keep the previous installation until your normal workflow is checked. The Source ZIP contains the complete source manifest for this version.
