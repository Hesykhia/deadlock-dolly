# Deadlock Dolly 0.6.25-alpha

Support for the October 6 Deadlock update (build 6757), plus a shot-editing fix.

## Highlights

- **Works with the new Deadlock build (6757).** *Before:* Dolly refused the October 6 game update. *After:* the native camera, replay startup, Game Follow, the health panel and Players/Depth work on build 6757, and the console unlocker is rebuilt for the new server. Reconstructed clip audio stays disabled on 6757 until its soundsystem review lands.
- **Deleting the first camera now starts the shot there.** *Before:* removing the leading camera left the shot anchored to the old start, so a front-end mistake could not be corrected. *After:* the shot rebases onto the new first camera, effects shift with it, and Undo restores the original start.

## Changes

- Reviewed the October 6 client (6757) as a relocation-class update: 157 reviewed client anchors resolved (92 code anchors relocation-equivalent, two replay spans and the observer-services schema record mapped manually, the Follow settings block re-resolved by its own registration code).
- engine2 changed hash only; every reviewed demo/replay accessor and vtable keeps its 6753 RVA.
- scenesystem producer is byte-identical modulo relocations at the same RVA; the `CSceneSystem` vtable and layout globals are unchanged.
- Rebuilt the bundled cvar unlocker for the 6757 server (new `Source2ServerConfig001` tuple) with its patch, PE audit and native shutdown/adapter tests.
- `dolly/ui/shot_commands.py`: deleting the leading camera rebases the shot (camera and effect times shift, the anchor advances) so the new first camera becomes shot time 0.

## Validation

Offline: 1,885 Python tests pass with 15 skipped; the native build and packaged portable-editor self-test pass; `tools/generate_compatibility.py --check --verify-game-dir` reports the installed 6757 game as reviewed (client, tier0 and resource identities, the observer-services schema record at offset 0xe98, and the scene/renderer pair). Live: one bounded owned replay (startup, unlocker, camera, Players/Depth and Stop / restore) is required before publishing.

## Preserved behavior and limits

All camera, timeline, framing-guide, spline, Follow, Bone Picker, Native DOF, Citadel DOF, graphics-profile and export features remain. On 6757, reconstructed clip audio is not enabled in this release; other features are unchanged from 0.6.24-alpha.

## Updating

Extract the new Windows ZIP into a fresh folder and run Dolly.exe. Python and Tcl/Tk are bundled. Keep the previous installation until your normal workflow is checked. The Source ZIP contains the complete source manifest for this version.
