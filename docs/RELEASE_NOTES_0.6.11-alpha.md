# Deadlock Dolly 0.6.11-alpha

This release brings together the overnight camera and compatibility hardening,
Players capture repair, Depth export completion fixes, clearer editor recovery,
and a new library of graphics profiles for Dolly replay sessions. Existing
camera drivers and editing/export features remain available.

## Highlights

- **Choose recording graphics for Dolly sessions.** *Before:* Changing between gameplay and recording quality required manual settings changes. *After:* Save, import, preview and select named graphics profiles, with the actual previous settings backed up and restored after the game exits.
- **More reliable camera startup and editor recovery.** *Before:* Console camera startup could stall on an unnecessary refresh, and returning to the editor could hide the original readiness failure behind an obsolete instruction. *After:* Dolly first checks camera response, guides safe health-panel restoration and retains actionable readiness errors without prematurely closing the console.
- **Players capture and complete Depth exports.** *Before:* The current game's Players producer could be rejected, and automatically completed Depth takes could skip final output work or lose pending timing restoration. *After:* A reviewed scene/renderer profile fixes producer selection; export completion and verified restoration finish through the normal workflow. Players remains alpha with known appearance limits.
- **Stronger compatibility and release checks.** *Before:* Optional feature failures could block independent camera functionality, compatibility facts were duplicated, and source archives omitted native files. *After:* Feature failures are better isolated, reviewed definitions are generated consistently, and complete source packages are checked with a clean local build.

## Graphics profiles for replay sessions

Open **Settings > Replay graphics profiles** to save your current graphics under
a name such as Recording, or import a saved `video.txt`. The import preview shows
the quality settings being saved and which fields are excluded. Profiles can be
renamed, deleted, previewed against the current settings, and selected for the
next Dolly launch. **Use current game settings** remains the default.

Profiles cover 15 supported quality controls, including shadows, fog, ambient
occlusion, textures, shader quality, bloom, anti-aliasing, motion blur and depth
of field. They use values from your own settings; Dolly does not invent a
universal Ultra preset.

The destination PC keeps its display mode, resolution, GPU information, upscaler,
render scale and unrecognized settings. Display launch options remain available
separately; borderless modes can still follow desktop resolution. Profiles do
not switch arbitrary `gameinfo.gi` files or repair unrelated mods.

Dolly resolves the signed-in Steam user's actual graphics file and backs up the
settings present immediately before each launch. Graphics stay active until the
game exits, then the original file is restored. Closing Dolly first hands cleanup
to its existing background helper. Interrupted sessions can recover on the next
launch or through **Settings > Troubleshooting & recovery > Recover configuration**.

If another edit changes the graphics file unexpectedly, Dolly preserves it,
retains the original backup and explains that recovery needs review. It does not
silently overwrite newer settings. Missing fields, unsupported file formats,
read-only files and ambiguous or unsafe paths are rejected before launch.

After camera support checks, available render controls are read back and included
in diagnostics. Differences or unreadable controls produce a warning without
forcing extra settings. A damaged profile library now reports its error after
the application window is ready, preserving access to the interface.

## Console / Legacy camera improvements

The Console driver first verifies that camera coordinates respond correctly.
Healthy paused cameras no longer perform an unnecessary adjacent-tick refresh
that could stall startup or switching to a saved view. The bounded refresh
fallback remains available when an actual response check fails.

Replay identity, startup cancellation, preload, intro handoff and camera checks
remain in place. Console capture, movement, saved-view switching and path
playback were exercised in owned local replay sessions.

When safe health-panel restoration needs a valid hero view, Stop now offers a
guided workflow: open replay controls, select a hero, then click **Restore after
selection**. The panel is not forced visible against an unverified camera.
This guided flow was completed with user participation and verified restoration.

## Clearer editor readiness and F8 recovery

The old “Complete 5 Check camera support” message referred to an obsolete
numbered setup flow. It now points to the current startup controls and retains
the preceding readiness failure when one is available.

A failed support check invalidates both partial results and stale permission
from an earlier successful check. Returning to the camera editor checks readiness
before changing camera ownership, HUD state or console access. A rejected F8
return therefore preserves the console instead of closing it prematurely.

A successful explicit support recheck can re-enable editing in the same healthy
session. There is no automatic replay reload or relaunch. The reported screenshot
could not identify the remote user's exact trigger; the corresponding failure
paths were reproduced and repaired in regression tests.

## Players layer capture on the current build

Players capture now selects a complete reviewed scene/renderer profile, including
the current producer entry point. Previously, a mixed set of old and new build
settings could select the wrong producer and reject capture.

Older reviewed profiles are retained. Module identity checks, source/destination
bounds, GPU identity matching, the 64-draw-per-image limit, original draw
forwarding and graphics-state restoration remain in place. The repair does not
add extra draw calls or accept unknown game builds.

The bounded Players check captured 30 frames with 816 exact GPU identity matches
and restored the collected settings. **Players remains alpha:** the tested view
had transparent opening frames and a dark player entering later. Coverage and
appearance across other scenes are not fully certified, and the separate black
silhouette issue is not claimed fixed by this release.

## Depth export completion and restoration

When the native recorder reaches its frame limit automatically, Dolly now finishes
the export through the desktop worker. Depth preview generation, shot metadata
and output finalization are no longer skipped just because recording has already
stopped in the native helper. Pending completion stays visible until that work
has finished, and repeated cleanup does not repeat a completed encode.

Original recording timing values remain saved until reset requests and readbacks
succeed. Failed restoration is reported and blocks a new take from overwriting
those originals. Independent resolution and player-view cleanup still runs when
another restoration step fails.

A separately approved Depth check completed **30 paired Color/Depth frames at
1920×1080 and 30 FPS**, a Depth MOV and **30 float EXRs**. Frame counts, timestamps,
decoded output and sampled geometry were checked independently. Timing, render
scale, HUD and collected configuration values were restored afterward. This
short software-encoded check does not certify every encoder or long recording.

## Compatibility and maintenance hardening

Optional Follow correction failures now remain local to that feature when the
core camera is independently supported. Malformed optional Follow or Confetti
diagnostics no longer make otherwise coherent camera status unreadable. Required
camera, process identity and protocol checks remain strict.

Partial optional-hook installation failures now cancel queued activation and
preserve safe pass-through behavior where required. This boundary is covered by
failure-injection tests; it is not a claim of isolation from arbitrary native
memory faults.

Shared reviewed definitions generate Python/native compatibility data for the
covered camera, preload, replay, Follow, attachment, sound and player-scene
contracts. Builds check for drift before replacing the previous native helper.
Historical profiles and their review gates remain available. Future unknown
Deadlock updates still require investigation; Dolly is not update-proof.

The source distribution now includes the previously omitted native render-class
implementation and header. Manifest regressions cover native source/header/test
families so a working checkout cannot conceal an incomplete source ZIP.

The earlier 0.6.10 Game Follow and health-panel field correction for build 6745 is
retained. Reusable research methods and evidence indexes were also maintained
locally to speed future investigations; private research and diagnostics are
excluded from the distributed source and Windows packages.

## Validation and remaining limits

- The combined source candidate passed **1,752 Python tests with 16 skips** before
  release packaging, including the damaged-profile startup regression.
- The final local release build runs the native checks, source regressions,
  packaged updater checks and the actual relocated editor startup check. The
  hardware-dependent 120-FPS encoder smoke test is explicitly excluded; it must
  not be counted as a pass. Exact build results accompany the local artifacts.
- Earlier bounded live checks covered Console guided restoration, native camera
  and Follow workflows, and a 30-frame 1080p color export. Players and Depth had
  separate bounded checks as described above.
- The new graphics-profile check confirmed both selected values in the game and
  exact restoration of all **42 collected configurations**, with normal exit and
  deployment cleanup. The complete attempt failed its window-size assertion:
  the preserved borderless settings opened at 2560×1440 despite stored 1920×1080
  dimensions. No recording or automatic retry occurred. All 15 profile controls
  are not visually certified by that two-control sample.
- Some earlier sessions repeated Deadlock's known Steam networking assertion.
  A PC watchdog reset reported after the Players session closed was audited;
  its cause remains unresolved. Neither that incident nor dark-player appearance
  is claimed fixed by this release.

These checks separate observed behavior from simulated tests and do not promise
compatibility with every mod, graphics configuration or future game update.

## Updating

Extract the complete **Deadlock_Dolly_0.6.11-alpha_Windows_x64.zip** and launch
`Dolly.exe` with its `_internal` folder beside it. Keep your shots and session logs,
especially while configuration recovery is pending. Existing per-user settings
and bindings are retained; the graphics library is stored separately and is
optional. The Source ZIP is for developers.
