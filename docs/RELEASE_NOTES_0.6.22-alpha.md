# Deadlock Dolly 0.6.22-alpha

Capture quality, encoder support and camera-feel release following 0.6.21-alpha.

## Highlights

- **Auto encoder picks your GPU's encoder.** *Before:* Auto always chose NVIDIA NVENC, so AMD and Intel users' recordings failed even though their cards support hardware encoding. *After:* Dolly detects the installed GPU and picks NVIDIA NVENC, AMD AMF or Intel Quick Sync automatically, falls back to the vendor-neutral Media Foundation encoder on unknown hardware, and shows the chosen encoder in the recording status.
- **Camera feel chooser.** *Before:* the free-camera mouse speed was a small number box hidden in the keybinds tab, and high-DPI mice made the camera spin. *After:* Settings has a Camera feel card with a slider and Very slow / Slow / Normal / Fast / Very fast presets, kept in sync with the keybinds field.
- **No more debug overlays over recordings.** *Before:* every Dolly session showed Deadlock's faint client-status logo mark and the match ID / server CPU debug text, even with the HUD hidden. *After:* both are hidden for the whole Dolly session, in the editor and while recording, and the rest of the replay HUD still works normally.

## Changes

- Added `dolly/encoder_select.py`: display-adapter enumeration, vendor-to-encoder mapping and fallback resolution, with the choice and adapter list logged for support.
- Auto validation and the recorder now resolve through the same vendor mapping; the export status line names the encoder actually in use.
- Added the Camera feel card to Settings with an exponential slider and presets; it and the keybinds number box stay in sync and persist normally.
- Added a compiled Panorama override pack (`pak02_dir.vpk`) built from `native/ui_override` by `tools/build_ui_override.py`; the launcher verifies its pinned hash and mounts it beside the confetti pack for native sessions, and cleanup still removes the session exactly.
- Extended the native release allowlist, the source manifest and the packaging tests to cover the override pack.

## Validation

Offline: 1,875 Python tests pass with 15 skipped; the native build passes 26 of 26 checks; the packaged editor passes its portable self-test. Live: bounded replay sessions verified the vendor-resolved encoder path, the Settings card and, with the override mounted, that both debug overlays are gone in the editor and in the F9 game UI while the replay HUD renders normally, with no pending restoration and byte-identical configuration restore.

## Preserved behavior and limits

All camera, timeline, framing-guide, spline, Follow, Bone Picker, graphics-profile and export features remain. Known opening-replay rendering and Players appearance limitations are unchanged, and no operating-system, driver or hardware stability fix is claimed. The overlay override replaces two stock Deadlock stylesheets, so it is refreshed with each game UI update as part of Dolly's per-build compatibility review.

## Updating

Extract the new Windows ZIP into a fresh folder and run Dolly.exe. Python and Tcl/Tk are bundled. Keep the previous installation until your normal workflow is checked. The Source ZIP contains the complete source manifest for this version.
