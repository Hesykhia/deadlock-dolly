# Deadlock Dolly 0.6.28-alpha

Support for the October 7 Deadlock hotfix (build 6763).

## Highlights

- **Works with the October 7 Deadlock hotfix (6763).** *Before:* the updated client changed `client.dll`, and Dolly refused the build so the replay editor would not start. *After:* native camera, replay startup, Game Follow, the health panel and Players/Depth work on 6763, and the bundled cvar unlocker is rebuilt for the new server.

## Changes

- Reviewed the 6763 client as a relocation-class update of 6762 (157 anchors: 70 relocation-equivalent, 23 raw, 1 remapped, 63 data); authored `native/profiles/deadlock-2026-10-07-6763-complete.json` and regenerated the compatibility outputs.
- Rebuilt the bundled cvar unlocker for the 6763 server; its reviewed `Source2ServerConfig001` tuple is unchanged from 6762 (`0x2a1aeb8`). Updated the PE audit, provenance and pins.
- Updated the editing baseline (`assets/editing/profile.json`) for the 6763 client and server.

## Validation

Offline: 1,888 Python tests pass with 15 skipped; the native build and packaged portable-editor self-test pass; `tools/generate_compatibility.py --check --verify-game-dir` reports the installed 6763 game as reviewed. Live: one bounded owned replay is required before publishing.

## Preserved behavior and limits

All camera, timeline, framing-guide, spline, Follow, Bone Picker, Native DOF, Citadel DOF, graphics-profile and export features remain. `engine2`, `tier0`, `scenesystem`, `soundsystem`, `resourcesystem` and `rendersystemdx11` are unchanged in 6763.

## Updating

Extract the new Windows ZIP into a fresh folder and run Dolly.exe. Python and Tcl/Tk are bundled. Keep the previous installation until your normal workflow is checked. The Source ZIP contains the complete source manifest for this version.
