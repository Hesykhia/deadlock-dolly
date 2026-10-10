# Deadlock Dolly 0.6.27-alpha

Support for the October 7 Deadlock update (build 6762), plus the Native DOF and
error-handling fixes.

## Highlights

- **Works with the October 7 Deadlock update (6762).** *Before:* the updated client changed `client.dll`, and Dolly refused the build so the replay editor would not start. *After:* native camera, replay startup, Game Follow, the health panel and Players/Depth work on 6762, and the bundled cvar unlocker is rebuilt for the new server.
- **Citadel Depth of Field keeps working after a Native DOF problem.** *Before:* once Native DOF failed on a game install, every depth-of-field control (including Citadel DOF) was blocked and errored. *After:* only the Native DOF pass is held back, and Citadel DOF plus the rest of the editor keep working.
- **Dolly no longer freezes on a repeated error.** *Before:* a repeated failure (for example moving a DOF slider after a Native DOF error) could stack error dialogs and leave Dolly needing a hard close. *After:* Dolly shows one clear message and stays responsive.
- **The Native DOF checkerboard guard is more reliable.** *Before:* the guard depended on the exact engine wording for a failed shader compiler, so some installs could still show the magenta/black checkerboard. *After:* the guard recognizes the failure regardless of wording and leaves Native DOF off with an explanation.

## Changes

- Reviewed the 6762 client as a relocation-class update of 6759 (157 anchors: 78 relocation-equivalent, 14 raw, 2 remapped, 63 data); authored `native/profiles/deadlock-2026-10-07-6762-complete.json` and regenerated the compatibility outputs.
- Rebuilt the bundled cvar unlocker for the 6762 server, whose `Source2ServerConfig001` tuple relocated to `0x2a1aeb8`; updated its PE audit, provenance and pins.
- Updated the editing baseline (`assets/editing/profile.json`) for the 6762 client and server.
- `dolly/controller.py`: the Native DOF refusal is gated on the project actually using `r_dof_override`, and shader-compiler failure detection is separator-normalized.
- `dolly/gui.py`: error dialogs coalesce so a burst of failures cannot stack modal dialogs.

## Validation

Offline: 1,888 Python tests pass with 15 skipped; the native build and packaged portable-editor self-test pass; `tools/generate_compatibility.py --check --verify-game-dir` reports the installed 6762 game as reviewed. Live: one bounded owned replay is required before publishing.

## Preserved behavior and limits

All camera, timeline, framing-guide, spline, Follow, Bone Picker, Native DOF, Citadel DOF, graphics-profile and export features remain. Reconstructed clip audio stays disabled until its soundsystem review lands (soundsystem is unchanged in 6762).

## Updating

Extract the new Windows ZIP into a fresh folder and run Dolly.exe. Python and Tcl/Tk are bundled. Keep the previous installation until your normal workflow is checked. The Source ZIP contains the complete source manifest for this version.
