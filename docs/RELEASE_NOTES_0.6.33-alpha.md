# Deadlock Dolly 0.6.33-alpha

Support for the October 8 Deadlock hotfix (6766).

## Highlights

- **Works with the October 8 Deadlock hotfix (6766).** *Before:* the updated client changed `client.dll` and `server.dll`, and Dolly refused the build so the replay editor would not start. *After:* native camera, replay startup, Game Follow and Players/Depth work on 6766, and the bundled cvar unlocker is rebuilt for the new server.
- **A Players layer export no longer leaves a stuck command window.** *Before:* starting a Players layer export could pop up a command window that stayed open, and the encoder could fail if it picked up the wrong libraries. *After:* the bundled encoder runs hidden in its own clean environment and reports a clear error instead of leaving a window open.

## Changes

- Added the reviewed `deadlock-2026-10-08-6766` camera profile and regenerated the compatibility contracts; refreshed the reviewed `client.dll` hash and the editing profile for the new build.
- Rebuilt and re-resolved the bundled cvar unlocker for the 6766 `server.dll` (new server hash and Source2ServerConfig001 tuple) and updated the launcher/native pins.
- Re-resolved the replay-camera code spans, rules global, observer-services schema record and the Follow settings block against the new image; the player-pawn health predicate is read from its reviewed vtable slot (`+0x4e0`).
- The Players layer encoder now spawns FFmpeg with a hidden window (`CREATE_NO_WINDOW`) and a clean external-program environment, and reports the encoder's exit status and stderr instead of a bare pipe error.

## Validation

Offline: 1,916 Python tests pass with 22 skipped; the native build and the packaged portable-editor self-test pass, and `generate_compatibility.py --check --verify-game-dir` passes against the installed build. Live (build 6766): a bounded startup / Game Follow / Player-POV run passed with the HUD hidden, the follow preserved through preparation and segment finish, the health panel restored on Stop, clean exit and exact config restoration.

## Preserved behavior and limits

All camera, timeline, framing-guide, spline, Follow, Bone Picker, Native/Citadel DOF, graphics-profile and export features remain, including the health-panel restore fix and the follow-camera export. Players appearance limits are unchanged.

## Updating

Extract the new Windows ZIP into a fresh folder and run Dolly.exe. Python and Tcl/Tk are bundled. Keep the previous installation until your normal workflow is checked. The Source ZIP contains the complete source manifest for this version.
