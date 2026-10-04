# Deadlock Dolly 0.6.14-alpha

A maintenance release for the desktop and in-game editors. This update
reorganizes existing behavior for easier maintenance; it does not introduce a
new theme library, change the editing workflow or remove features. The mod-loading
repair from 0.6.13-alpha is retained.

## Highlights

- **Familiar controls, easier upkeep.** *Before:* Shared controls and editor actions were maintained in several large, connected files. *After:* They have clearer shared owners, while your layouts, shortcuts, camera tools and saved settings stay the same.
- **In-game tools kept together.** *Before:* Panel and Bone Picker drawing shared a file with the graphics hook lifecycle. *After:* Their presentation is separated, with the existing input, resizing and cleanup behavior retained and checked against the previous version.

## Complete maintenance changes

- Shared desktop cards, disclosure sections, scrolling containers and spacing
  have one widget module. Existing callers retain their compatibility entry points.
- Theme initialization is centralized. The current palette, typography, rounded
  controls, selection behavior and wheel handling are preserved.
- Library, Settings and Export pages own their widgets through explicit state
  and action interfaces. Graphics-profile access uses the existing guarded
  profile operations, preserving preference writes and error ordering.
- Background operations, event delivery, shared shot edits and layer scheduling
  have distinct owners. Queue limits, cancellation, failure cleanup, camera
  history, export preparation and restoration order are preserved.
- Native editor value mapping, cached publication and action dispatch are
  separated. Bone Picker receives an explicit publishing callback. The two
  audited UI import cycles have been removed; broader lifecycle/transport
  refactoring is outside this release.
- ImGui panel/font/guide rendering and Bone Picker presentation are separated
  from DX11 hooks and resource ownership. Portrait textures stay with the
  renderer. Draw order, input capture, context restoration and framebuffer
  scaling are retained.
- Added characterization and boundary coverage for these responsibilities.
  Existing behavior tests remain, including portrait pixel readback and
  request-change clearing/replacement against both old and new implementations.
- Refreshed the pinned LGPL shared FFmpeg download used by clean source builds
  and documented its refresh procedure. SHA-256 verification remains required.

## Retained features and limitations

Native and Console camera playback, Game Follow, Bone Picker, Undo/Redo, graphics
profiles, Depth/Players/audio export, ReShade, mod-mount carry and updating remain
included. Settings and project formats are unchanged. Existing alpha limitations,
including Players appearance and opening-zipline visuals, remain; this release
makes no new game-build compatibility or capture-quality claim.

## Validation and scope

Desktop layout/theme snapshots, action publication traces and native rendering
bodies were compared with the prior implementations. Three WARP panel screenshots
match byte for byte. The post-0.6.13 source checkpoint passed 1,831 Python tests
with 16 skips. The UI-6 native checkpoint passed all 26 enabled native checks.
The release build repeats the full enabled checks, portable editor relocation
and updater self-tests; exact results accompany the local build evidence.

Hardware encoder smoke is excluded. No new live game session was run for this
release; offline checks do not certify the rebuilt binary in Deadlock. FFmpeg's
fresh download matches the upstream checksum and passes a software mux/decode
regression. No live recording, game audio capture or extra layer draws were used.

## Updating

Extract the complete Windows x64 ZIP and keep `_internal` beside `Dolly.exe`.
Close any Dolly editing session before replacing that installation. Existing
projects and saved graphics profiles remain usable. The Source ZIP is for
maintainers and includes the matching native source and compatibility inputs.
