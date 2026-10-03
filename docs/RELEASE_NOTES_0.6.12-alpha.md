# Deadlock Dolly 0.6.12-alpha

This update fixes hidden replay controls at automatic startup, prevents Dolly's
panel from opening early, and corrects in-game overlay scaling. It retains the
camera, graphics-profile and export features from 0.6.11-alpha.

## Highlights

- **F9 replay controls return after startup.** *Before:* Dolly could pause while Deadlock's opening sequence still hid the replay timeline and hero controls. *After:* Startup waits for the game's HUD transition to finish before pausing, so F9 can show the controls immediately.
- **A cleaner startup.** *Before:* Closing the startup console or resetting the editor while loading could open Dolly's panel too early. *After:* The panel stays closed until camera support is verified, while recovery shortcuts remain available.
- **The in-game panel scales correctly.** *Before:* Different rendering and window sizes could clip or misplace parts of the panel. *After:* Dolly scales its drawing and clipping to the actual render surface, keeping the panel correctly positioned without changing your resolution.

## Replay startup and F9

Deadlock can finish switching its opening camera before it finishes hiding the
normal HUD for that opening sequence. Dolly previously paused as soon as the
camera was ready. That could freeze the replay while its timeline, hero health
and spectator controls were still hidden, even though F9 correctly returned
camera and mouse control to the game.

Automatic startup now requires both the settled gameplay camera and the end of
the stock HUD takeover. It observes the game's state and keeps the existing
startup timeout; it does not use a fixed delay, seek ahead or force HUD classes.
F9 itself does not automatically resume the replay.

The checks that make health-panel restoration safe are unchanged. Game Follow,
manual camera controls, replay seeking and recovery remain available. Seeking
back into an opening cinematic does not override Deadlock's own HUD behavior.

## Startup panel and display scaling

Two startup paths could give Dolly's panel ownership before camera support was
verified: closing the console and stopping/resetting the editor while loading a
replay. Both now retain the closed panel state until verification succeeds.
An open recovery console stays accessible, and Stop after verification retains
its normal panel behavior.

The DirectX 11 overlay now uses the render surface dimensions when scaling its
viewport and clipping rectangles. This fixes clipping when that surface differs
from the window size. This update does not force 1080p or alter saved display
settings. A previously reported transient resolution change was not attributed
to a confirmed writer, so this release does not claim a separate resolution-reset
fix.

## Retained features

Named Dolly-only graphics profiles, Console fallback, Game Follow, camera paths,
Depth exports, Players capture, audio and ReShade remain included. This release
does not add a new Depth or Players capture implementation. The prior alpha
limitations of Players appearance and opening-zipline visuals remain.

For the larger preceding update, see the
[0.6.11-alpha release notes](RELEASE_NOTES_0.6.11-alpha.md).

## Validation and scope

- A bounded owned-replay check on the reviewed Deadlock build 6745 confirmed the
  stock replay HUD before editing, immediately after F9, and after an F8/F9
  cycle. The replay stayed paused at the same tick during both handoffs.
- The game remained at 2560x1440. All 42 saved configuration files were restored
  exactly; the process exited normally with no detected assertion or crash,
  pending restoration or leftover Dolly deployment.
- Regression coverage includes an active or changing HUD takeover, missing or
  unreadable state, invalid object types/counts, cancellation and changed replay
  identity. The source suite ran 1,764 tests with 16 skips before packaging.
- The overlay scaling regression exercises differing window/render sizes using
  a software graphics device. The local distribution build also checks native
  code, the Python suite, the relocated portable editor and the updater. Its
  hardware-dependent encoder smoke is excluded.

The final versioned package is built locally from the validated changes. No
additional live game session is required for the version and packaging changes;
the rebuilt release binary is not separately live-certified. This HUD check
does not extend the earlier Depth, Players, audio or long-recording validation.

## Updating

Extract the complete Windows x64 ZIP and keep `_internal` beside `Dolly.exe`.
Close an existing Dolly editing session before replacing that installation.
Your project files and saved profiles remain usable. The Source ZIP is for
maintainers and includes the native source and reviewed compatibility inputs.
