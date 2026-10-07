# Deadlock Dolly 0.6.26-alpha

Support for the second October 6 Deadlock patch (build 6759).

## Highlights

- **Works with the October 6 hotfix (6759).** *Before:* the second October 6 game patch changed `client.dll` and `server.dll` again, and Dolly refused the updated client. *After:* native camera support follows the hotfix (re-reviewed 6757 -> 6759) and the bundled console unlocker is rebuilt for the new server. Build 6757 remains accepted.

## Changes

- Reviewed the 6759 client as a relocation-class update of the reviewed 6757 client (157 anchors resolved); `engine2`, `scenesystem`, `tier0`, `resourcesystem` and `rendersystemdx11` are unchanged.
- Rebuilt the bundled cvar unlocker for the 6759 server (new server hash; the reviewed `Source2ServerConfig001` tuple is unchanged from 6757) with its patch, PE audit and native shutdown/adapter tests.

## Validation

Offline: 1,885 Python tests pass with 15 skipped; the native build and packaged portable-editor self-test pass; `tools/generate_compatibility.py --check --verify-game-dir` reports the installed 6759 game as reviewed. Live: one bounded owned replay is required before publishing.

## Preserved behavior and limits

All camera, timeline, framing-guide, spline, Follow, Bone Picker, Native DOF, Citadel DOF, graphics-profile and export features remain. On 6759, reconstructed clip audio stays disabled until its soundsystem review lands; other features are unchanged from 0.6.25-alpha.

## Updating

Extract the new Windows ZIP into a fresh folder and run Dolly.exe. Python and Tcl/Tk are bundled. Keep the previous installation until your normal workflow is checked. The Source ZIP contains the complete source manifest for this version.
