# Deadlock Dolly 0.6.13-alpha

This update restores mod loading during Dolly editing sessions. It retains the
camera, graphics-profile and export features from 0.6.12-alpha.

## Highlights

- **Mods load with Dolly again.** *Before:* launching through Dolly replaced `gameinfo.gi` with Dolly's own configuration and dropped every mod mount, so skin and HUD mods were missing for the whole session. *After:* Dolly carries your installed mod mounts (Deadlock Mod Manager, Grimoire or a manual setup) into its temporary configuration, and your original file is still restored exactly on exit.
- **Uncompiled HUD files are still caught early.** *Before:* a stale loose Panorama file inside a mounted mod folder could crash the game before Dolly connected. *After:* Dolly names the exact file and refuses before changing anything.

## Why mods stopped loading

Mod managers enable mods by adding search paths to `game/citadel/gameinfo.gi`.
Deadlock Mod Manager writes `citadel/addons` and its shard folders, Grimoire
adds `citadel/grimoire`, `citadel/addons1..9` and its Deadworks server path, and
the manual modding guide adds `AddonRoot`, `OfficialAddonRoot` and
`AddonConfig` entries.

Dolly backs up that file and mounts its own reviewed editing configuration for
each session, then restores your bytes on exit. Through 0.6.1-alpha the
reviewed configuration happened to include addon mounts, so mods loaded. The
0.6.2-alpha fix for a startup crash removed those mounts, and from then on the
session configuration no longer referenced any mod folders. The effect was
session-only and silent: your file was restored untouched, but mods simply were
not mounted while Dolly drove the game.

## What changed

Dolly now reads the addon entries already present in your installed
`gameinfo.gi` and carries them into the temporary session file:

- `Game` mounts for `citadel/addons`, shard folders (`addons1..9`, including
  DMM profile folders), `citadel/grimoire` and `citadel/deadworks_addons/vpks`,
  in their original order.
- `Mod` and `Write` paths for `citadel` and `core`. Mounting folders ahead of
  the base game without these reproduces the game's "Unable to read default
  keybinding configuration" startup failure, so Dolly supplies them when a file
  mounts addons without declaring them.
- `AddonRoot`, `OfficialAddonRoot` and an `AddonConfig` block when your file has
  them.

Everything else - competitive ConVars, rendering overrides, unrelated search
paths and launch settings - still comes from Dolly's reviewed editing
configuration, and the reviewed file on disk is never modified. Dolly's
temporary unlocker mount keeps its place ahead of the mod mounts.

The pre-launch loose-file check now also scans the Panorama directories inside
mounted addon folders. A loose `panorama/layout/*.xml` or
`panorama/scripts/*.js` file there can shadow the updated game's compiled UI
under development mode and crash startup; Dolly names the exact relative path
and refuses before changing anything. Normal VPK mods are unaffected.

## Retained features

Camera paths, native camera, Game Follow, Bone Picker, graphics profiles, Depth
and Players capture, audio, ReShade and the updater remain included. No features
were removed. The known alpha limitations of Players appearance and
opening-zipline visuals remain.

## Validation and scope

- Regression coverage includes DMM mounts and profile shards, Grimoire priority
  and overflow mounts, Mod/Write synthesis, AddonConfig carry, unchanged stock
  input, launch settings not carried, and mounted-addon loose-file refusal. The
  full source suite ran 1,776 tests with 17 skips.
- The local distribution build checks native code, the Python suite, the
  relocated portable editor and the updater. Its hardware-dependent encoder
  smoke is excluded.
- No new live game session was run for this update; all previous live
  allowances remain consumed. The rebuilt release binary is not separately
  live-certified.

## Updating

Extract the complete Windows x64 ZIP and keep `_internal` beside `Dolly.exe`.
Close an existing Dolly editing session before replacing that installation.
Your project files and saved profiles remain usable, and your mod manager keeps
working normally outside Dolly. The Source ZIP is for maintainers and includes
the native source and reviewed compatibility inputs.
