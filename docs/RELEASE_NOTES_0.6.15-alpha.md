# Deadlock Dolly 0.6.15-alpha

Session lifecycle and configuration maintenance, following 0.6.14-alpha.

## Highlights

- **Session maintenance.** *Before:* Launching, configuration recovery and cleanup shared tightly connected code. *After:* These responsibilities are separated and regression-tested, preserving the existing editing workflow.
- **Windows cleanup checks.** *Before:* A linked-folder safety test could be skipped without Windows symlink privileges. *After:* It also runs with a Windows junction, checking that cleanup leaves linked files untouched.

## Changes

- Shared KeyValues parsing and launch errors now have independent owners.
- Atomic file replacement and ordinary-path guards are shared by configuration and cleanup code.
- Game configuration journals and restoration live in a dedicated transaction module.
- Console-value parsing is shared directly with graphics-profile checks.
- Installation validation, read-only process queries and coordinated configuration restoration have distinct owners. The lifecycle import cycle is removed.
- Existing launcher entry points remain compatible. Process ownership, startup gates, restoration order, cleanup retries and conflicting-file protection are preserved.
- Regression tests cover malformed inputs, failed writes, recovery conflicts, pending restoration, process ownership and cleanup of linked directories. Windows junction coverage no longer needs symlink privileges.

## Validation

The lifecycle source passed 1,874 Python tests (15 skipped) and a subsequent 163-test focused check with no skips. A bounded local replay smoke verified normal startup, F8/F9, normal exit, deployment removal and exact restoration of all 42 monitored configuration files at 2560x1440. Offline before/after comparisons also checked parser results, transaction states, restoration order and cleanup failure paths.

Release packaging runs the local native/Python checks, packaged editor/updater self-tests and archive verification. The hardware-dependent native encoder smoke is excluded. The release rebuild is separately identified from the native binary used for the source live smoke; this is not exhaustive live certification of every capture mode or graphics preset.

## Preserved behavior and limits

This is a maintenance refactor, not a new startup algorithm or journal-policy change. Existing camera, Follow, Bone Picker, graphics-profile and export features remain included, as do the 0.6.13 mod-loading repair and 0.6.14 UI/FFmpeg maintenance.

Journal size/duplicate-key policies and external-writer race behavior are unchanged. Known opening-replay rendering and Players appearance limitations are not addressed by this release. No operating-system, driver or hardware stability fix is claimed.

## Updating

Extract the new Windows ZIP into a fresh folder and run Dolly.exe. Python and Tcl/Tk are bundled. Keep the previous installation until your normal workflow is checked. The Source ZIP contains the complete source manifest for this version.
