# Deadlock Dolly 0.6.16-alpha

Deadlock compatibility update for the October 4, 2026 game update
(ClientVersion 6746), following 0.6.15-alpha. This is a compatibility-only
release: no editing features changed.

## Highlights

- **Game update support.** *Before:* The October 4 game update blocked Dolly's native startup. *After:* Dolly is reviewed for the new build, so startup, replay loading, camera paths and editing work again.
- **cvar unlocker refreshed.** *Before:* The bundled unlocker refused the updated server build. *After:* It has its own reviewed build for the new game version and verifies the new server fingerprint before mounting.
- **Health HUD handoff restored.** *Before:* On the new build the spectator hero handoff could not verify, leaving a stuck healthbar and refusing path playback. *After:* The handoff verifies and path playback works.
- **Selected-player effect filter verified.** *Before:* Native startup could stop with "The selected-player effect filter could not be verified". *After:* The effect filter is reviewed for the new build.

## Changes

- Reviewed Build 6746 compatibility profile: every reviewed code anchor is relocation-clean, and the camera wrapper, replay, follow and health spans pair one-for-one with the reviewed 6745 bodies.
- Runtime contract, compatibility manifest, generated outputs and the native bridge rebuilt for 6746. The editing profile and launcher pins accept the new client and server identities.
- Bundled cvar unlocker rebuilt: the Source2ServerConfig001 secondary table moved with the update while all three reviewed method bodies and the this-8 thunks are unchanged.
- The gameplay-effect filter table and the Follow settings block now carry explicit per-build values, so a future update cannot silently re-point them at a different client.

## Validation

Offline: compatibility verification passes against the installed game (client identity, 52 code spans, schema field, scene/renderer pair); the native bridge passes 26 of 26 checks with the hardware-dependent encoder smoke excluded; 1,874 Python tests pass with 15 skipped. One bounded local replay run verified native startup, unlocker confirmation, replay playback, the health HUD handoff and normal stop/restore, with the temporary deployment removed and the original configuration restored.

## Preserved behavior and limits

All existing camera, Follow, Bone Picker, graphics-profile and export features remain. Known opening-replay rendering and Players appearance limitations are unchanged, and no operating-system, driver or hardware stability fix is claimed.

## Updating

Extract the new Windows ZIP into a fresh folder and run Dolly.exe. Python and Tcl/Tk are bundled. Keep the previous installation until your normal workflow is checked. The Source ZIP contains the complete source manifest for this version.
