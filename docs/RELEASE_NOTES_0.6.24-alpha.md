# Deadlock Dolly 0.6.24-alpha

Playback dead-end fix following 0.6.23-alpha.

## Highlights

- **Playback continues when the game's health panel cannot be verified.** *Before:* Dolly hides the game's own-health panel while editing. When a game build's spectator player context could not be verified, that panel stayed pending and Play refused with "Previous settings still need restoration" — and the suggested escape (select a hero and use Stop / restore) could not complete, leaving no way forward. *After:* playback proceeds with the panel left safely hidden, and it is restored later once a verified hero view exists.

## Changes

- `Controller._health_panel_held` gained a `require_full_hud` switch. The guarded in-process replay-reload path keeps the strict rule (the full HUD hide must still be in place); playback only requires the own-health panel to remain hidden.
- `Controller.play` uses the relaxed check, so a held-but-unverifiable health panel no longer blocks shot playback.
- Added regression tests for the held-panel state and for playback remaining available after the main HUD has been restored.

## Validation

Offline: 1,880 Python tests pass with 15 skipped; the native helper build and the packaged portable-editor self-test pass during the release build. The reported sequence is reproduced from the affected install's log: the health reveal is deferred (`selected player object type differs from the reviewed build`), the main HUD restores, and only the own-health panel stays pending.

Live: confirming playback continues on that install while the panel stays hidden is the next in-game check.

## Preserved behavior and limits

All camera, timeline, framing-guide, spline, Follow, Bone Picker, Native DOF, Citadel DOF, graphics-profile and export features are unchanged. The underlying player-context mismatch is a reviewed-build profile issue: on that game build the own-health panel and Follow verification may stay unavailable until a compatibility profile is generated for the updated `client.dll`. This release removes the dead-end; it does not add build support.

## Updating

Extract the new Windows ZIP into a fresh folder and run Dolly.exe. Python and Tcl/Tk are bundled. Keep the previous installation until your normal workflow is checked. The Source ZIP contains the complete source manifest for this version.
