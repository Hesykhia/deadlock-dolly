# Deadlock Dolly 0.6.32-alpha

Restores the health/ability panel reliably after you Stop editing.

## Highlights

- **The health/ability panel restores after editing.** *Before:* after Stop, Dolly could report the health panel as "pending" and leave the ability panel hidden until you re-selected a hero, because a reviewed predicate address no longer matched the installed build. *After:* Dolly reads the player-pawn predicate straight from the reviewed pawn vtable, so the panel restores on Stop.

## Changes

- Resolved `FollowTarget.PLAYER_PREDICATE` from the player-pawn vtable slot (`+0x4e0`), like `PLAYER_DATA_PREDICATE`, instead of an instruction-map translation that no longer matched the installed build. The reviewed compatibility profile and the generated runtime files now carry the resolved predicate.

## Validation

Offline: 1,912 Python tests pass with 22 skipped; the native build and the packaged portable-editor self-test pass. Live (build 6765): a bounded startup / Game Follow / Player-POV run restored the health panel on Stop with an empty pending-restoration state, clean exit and exact config restoration.

## Preserved behavior and limits

All camera, timeline, framing-guide, spline, Follow, Bone Picker, Native/Citadel DOF, graphics-profile and export features remain, along with the October 8 hotfix (6765) support shipped in 0.6.31. Players appearance limits are unchanged.

## Updating

Extract the new Windows ZIP into a fresh folder and run Dolly.exe. Python and Tcl/Tk are bundled. Keep the previous installation until your normal workflow is checked. The Source ZIP contains the complete source manifest for this version.
