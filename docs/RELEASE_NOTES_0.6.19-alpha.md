# Deadlock Dolly 0.6.19-alpha

Follow-up release to 0.6.18-alpha with two camera-editing refinements.

## Highlights

- **Scrub the Shot timeline without grabbing a camera.** *Before:* a press near a camera mark started moving it, so scrubbing was hard on a busy track. *After:* a plain drag always scrubs; hold **Alt** and drag a mark to retime that view. The mark highlights and shows its arrival time while Alt is held.
- **Smooth is the default curve again.** *Before:* new shots and captures started on spline. *After:* they start on smooth, and spline is one click away in the new **Path curve** control in the Camera tab header (or the Coordinates / timing dialog). Saved shots keep the curve they were saved with.

## Changes

- Camera ticks require Alt+drag on the Shot timeline; hover highlighting, the tooltip and the resize cursor only appear with Alt. Ctrl+click still types an exact time.
- New shots and captures default to smooth; loading a saved shot no longer converts its stored "smooth" to spline.
- New **Path curve** selector (smooth / spline / linear) in the Framing curves header; the Coordinates / timing dialog lists smooth first.
- Spline files still record project format version 10; smooth files keep their normal version.

## Validation

Offline: 1,894 Python tests pass with 15 skipped; the native build passes 26 of 26 checks; the overlay smoke asserts that a plain drag scrubs without moving a tick and that Alt+drag commits exactly one revision-bound time change. Live: one bounded replay session verified both behaviors and the Path curve selector, with the temporary deployment removed and the original configuration restored.

## Preserved behavior and limits

All camera, timeline, framing-guide, spline, Follow, Bone Picker, graphics-profile and export features remain. Known opening-replay rendering and Players appearance limitations are unchanged, and no operating-system, driver or hardware stability fix is claimed.

## Updating

Extract the new Windows ZIP into a fresh folder and run Dolly.exe. Python and Tcl/Tk are bundled. Keep the previous installation until your normal workflow is checked. The Source ZIP contains the complete source manifest for this version.
