# Deadlock Dolly 0.6.21-alpha

Compatibility release for the October 5 Deadlock update (build 6753).

## Highlights

- **Works with the new game build.** *Before:* Dolly could not attach to the October 5 Deadlock update, so startup stopped at the reviewed-build check. *After:* startup, the console unlocker, replay loading, camera editing and Players/audio all work on build 6753.
- **Rebuilt console unlocker.** *Before:* the bundled unlocker matched the previous server build. *After:* it is rebuilt for the new server, with the same bounded startup and exact configuration restore.
- **Players and audio module support updated.** *Before:* the scene, sound and renderer module pins matched the previous engine build. *After:* the new scenesystem, soundsystem and rendersystemdx11 builds are recognized, so the Players layer and reconstructed audio keep working.

## Changes

- Re-reviewed every client-side camera, Follow, preload and schema anchor for build 6753, including the moved settings block, the player predicates and the preload manager object.
- Updated the engine2, resourcesystem, scenesystem, soundsystem and rendersystemdx11 fingerprints and profiles.
- Added explicit effects-table literals for the new client build so the gameplay-effect screen keepout cannot be re-pointed by a hash refresh.
- Regenerated the reviewed compatibility outputs and updated the pinned test fixtures to the new build.

## Validation

Offline: 1,862 Python tests pass with 15 skipped; the native build passes 26 of 26 checks; the offline module/code/schema verification passes against the installed game. Live: a bounded replay session verified startup, the unlocker confirmation and configuration restore, map and shader preload, replay load, camera controls, the attach schema and the Players/audio passes on build 6753.

## Preserved behavior and limits

All camera, timeline, framing-guide, spline, Follow, Bone Picker, graphics-profile and export features remain. Known opening-replay rendering and Players appearance limitations are unchanged, and no operating-system, driver or hardware stability fix is claimed.

## Updating

Extract the new Windows ZIP into a fresh folder and run Dolly.exe. Python and Tcl/Tk are bundled. Keep the previous installation until your normal workflow is checked. The Source ZIP contains the complete source manifest for this version.
