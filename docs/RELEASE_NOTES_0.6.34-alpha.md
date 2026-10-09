# Deadlock Dolly 0.6.34-alpha

Native Depth of Field works again on game installs that cannot compile the DOF
shader.

## Highlights

- **Native Depth of Field works on installs that showed the black checkerboard.** *Before:* applying Native DOF made Dolly force the game to recompile its DOF shader. Many installs ship no shader compiler or source, so that recompile always failed and the engine drew its magenta/black error material over the view. *After:* Dolly skips that forced recompile and the engine renders Native DOF from the shader it already ships, so the effect works and the checkerboard is gone.

## Changes

- `ensure_native_dof_shader_support` now checks the game's `bin/win64` for the DOF shader-compiler files (`vfx_dx11.dll` and `slang.dll`). When they are missing, it skips `mat_forcereloadshaders dof` instead of forcing a recompile that can only fail, and lets the pass apply from the engine's shipped compiled `dof` shader.
- When the compiler files are present, the existing reload-and-refuse safety net is unchanged.

## Validation

Offline: 1,918 Python tests pass with 22 skipped; the native build and the packaged portable-editor self-test pass. Live (build 6766): a bounded owned-replay run applied Native DOF with the forced recompile skipped, confirmed no shader-compile error, allowed both Native and Citadel DOF, and restored the session exactly.

## Preserved behavior and limits

All camera, timeline, framing-guide, spline, Follow, Bone Picker, Native/Citadel DOF, graphics-profile and export features remain, including the October 8 hotfix (6766) support and the health-panel restore fix. Players appearance limits are unchanged.

## Updating

Extract the new Windows ZIP into a fresh folder and run Dolly.exe. Python and Tcl/Tk are bundled. Keep the previous installation until your normal workflow is checked. The Source ZIP contains the complete source manifest for this version.
