# Deadlock Dolly 0.6.31-alpha

Support for the October 8 Deadlock hotfix (6765), follow-camera (Player POV)
export without the replay HUD, and a larger Players capture draw budget.

## Highlights

- **Works with the October 8 Deadlock hotfix (6765).** *Before:* the updated client changed `client.dll` and `server.dll`, and Dolly refused the build so the replay editor would not start. *After:* native camera, replay startup, Game Follow and Players/Depth work on 6765, and the bundled cvar unlocker is rebuilt for the new server.
- **Export a follow camera without turning on the replay HUD.** *Before:* recording a Player POV (follow camera) required pressing F9 and selecting a hero, and starting the export stopped the Game Follow and brought the replay HUD back. *After:* pick a hero with Game Follow — which already runs with the HUD hidden — and record or export straight away. The follow keeps running while the segment records, and no F9 step is needed.
- **Busier fights no longer break a Players capture.** *Before:* a Players layer capture failed with "failed player layer exceeded 64 draws per image; incomplete output rejected" when a single frame contained more than 64 player draws. *After:* the per-image draw budget is doubled from 64 to 128, so crowded moments capture completely.

## Changes

- Added the reviewed `deadlock-2026-10-08-6765` camera profile and regenerated the compatibility contracts; refreshed the reviewed `client.dll` hash and the editing profile for the new build.
- Rebuilt and re-resolved the bundled cvar unlocker for the 6765 `server.dll` (new server hash and Source2ServerConfig001 tuple) and updated the launcher/native pins.
- `prepare_pov_recording` now accepts an active Game Follow as the hero selection instead of requiring the replay HUD, and no longer calls Stop (which stopped the follow and revealed the HUD) on that path.
- `finish_pov_recording` keeps an active Game Follow rig and the hidden HUD after a segment instead of restoring the replay UI.
- The Player POV export guard and its message accept `game_follow_active` as well as `game_ui_visible`.
- Raised `AggregateDrawLimit` from 64 to 128 in the native player capture and rebuilt the native helper.

## Validation

Offline: 1,916 Python tests pass with 22 skipped; the native build and packaged portable-editor self-test pass. Live (build 6765): a bounded startup / Game Follow / Player-POV preparation run passed with the HUD hidden, the follow preserved through preparation and segment finish, clean exit and exact config restoration.

## Preserved behavior and limits

All camera, timeline, framing-guide, spline, Follow, Bone Picker, Native/Citadel DOF, graphics-profile and export features remain. The health/ability panel can still be reported as pending on this build because its player-pawn predicates differ from the reviewed build; use Stop / restore after selecting a hero to reveal it. Players appearance limits are unchanged.

## Updating

Extract the new Windows ZIP into a fresh folder and run Dolly.exe. Python and Tcl/Tk are bundled. Keep the previous installation until your normal workflow is checked. The Source ZIP contains the complete source manifest for this version.
