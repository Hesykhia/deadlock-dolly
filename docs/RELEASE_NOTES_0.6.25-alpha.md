# Deadlock Dolly 0.6.25-alpha

Support for the two October 6 Deadlock updates (builds 6757 and 6759), a shot-editing fix, and health-panel hardening.

## Highlights

- **Works with the October 6 Deadlock updates (6757 and 6759).** *Before:* both October 6 game patches changed the client and server, and Dolly refused the updated client. *After:* native camera, replay startup, Game Follow, the health panel and Players/Depth work on 6757 and 6759, and the console unlocker is rebuilt for each server. Reconstructed clip audio stays disabled until its soundsystem review lands.
- **Deleting the first camera now starts the shot there.** *Before:* removing the leading camera left the shot anchored to the old start, so a front-end mistake could not be corrected. *After:* the shot rebases onto the new first camera, effects shift with it, and Undo restores the original start.
- **Export and F9 no longer stall on the health panel.** *Before:* a stale player-predicate value made the health-panel handoff retry for five seconds, so F9 was slow and exports were blocked with a pending-restoration error. *After:* the predicate is corrected, the handoff fails fast instead of retrying, and a cosmetic panel can no longer block export.

## Changes

- Reviewed the 6757 and 6759 clients as relocation-class updates (157 anchors each); `engine2`, `scenesystem`, `tier0`, `resourcesystem` and `rendersystemdx11` are unchanged across them.
- Rebuilt the bundled cvar unlocker for each changed server (6757 and 6759) with its patch, PE audit and native shutdown/adapter tests.
- Reviewed the editing baseline (`assets/editing/profile.json`) for the new client/server, and corrected the reviewed player-predicate pin (the player-pawn vtable slot) so the health handoff verifies.
- A hero-handoff that cannot verify no longer aborts the HUD/cursor restore, and export/replay recovery tolerates a held own-health panel (mirroring playback).
- `dolly/ui/shot_commands.py`: deleting the leading camera rebases the shot (camera and effect times shift, the anchor advances) so the new first camera becomes shot time 0.

## Validation

Offline: 1,885 Python tests pass with 15 skipped; the native build and packaged portable-editor self-test pass; `tools/generate_compatibility.py --check --verify-game-dir` reports the installed 6759 game as reviewed. Live: one bounded owned replay is required before publishing.

## Preserved behavior and limits

All camera, timeline, framing-guide, spline, Follow, Bone Picker, Native DOF, Citadel DOF, graphics-profile and export features remain. On 6757/6759, reconstructed clip audio is not enabled in this release.

## Updating

Extract the new Windows ZIP into a fresh folder and run Dolly.exe. Python and Tcl/Tk are bundled. Keep the previous installation until your normal workflow is checked. The Source ZIP contains the complete source manifest for this version.
