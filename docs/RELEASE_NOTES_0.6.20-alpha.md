# Deadlock Dolly 0.6.20-alpha

Performance and control polish release following 0.6.19-alpha.

## Highlights

- **Smoother desktop editor.** *Before:* dropdowns, sliders and scrolling could feel sticky even while idle. *After:* the interface stays quiet when nothing is happening and redraws only when something changes.
- **Smooth page scrolling.** *Before:* precision touchpads and high-resolution wheels dropped scroll steps, and the scrollbar could jump when labels resized. *After:* wheel deltas accumulate into consistent motion and the scroll region only updates when it actually changes.
- **Zoom and pan the in-game Shot timeline.** *Before:* a timeline with many cameras was crowded and hard to work with. *After:* the mouse wheel zooms around the pointer, right-drag pans, and Alt+drag still retimes a camera tick.
- **No more panel flicker.** *Before:* moving the mouse quickly over the in-game panel could make it blink off and back for a frame. *After:* the overlay retries the render lock briefly instead of skipping the frame.
- **Paused camera retired.** *Before:* the desktop Paused camera button duplicated features the game now provides. *After:* it is gone from the Camera tab and File menu; the in-game panel and legacy driver are unchanged.

## Changes

- Idle poll runs at 250 ms and returns to 100 ms while a session or work is active. Widgets, status texts and the console-smoothing row are only updated on real changes.
- Graph wheel/pan/resize redraws are coalesced into one idle pass; the path overview moves only its playhead marker unless the project changed.
- `ScrollPage` scrolls in fixed 20 px units with accumulated wheel deltas.
- The Shot timeline keeps a visible time window: wheel zooms (minimum 0.1 s), right-drag pans, and off-window ticks are skipped. Hovering the slider claims the mouse wheel so the panel's scroll region cannot swallow it.
- Present retries the overlay render lock for up to 2 ms before falling back to the previous skip behavior.

## Validation

Offline: 1,899 Python tests pass with 15 skipped; the native build passes 26 of 26 checks, including smoke assertions that a plain drag scrubs, Alt+drag commits one revision-bound time change, and the Shot timeline wheel-zooms, right-drag pans and restores its full range. Live: bounded replay sessions verified the smoother desktop interactions, the timeline zoom/pan, and the flicker fix while scrubbing the mouse over the panel.

## Preserved behavior and limits

All camera, timeline, framing-guide, spline, Follow, Bone Picker, graphics-profile and export features remain. Known opening-replay rendering and Players appearance limitations are unchanged, and no operating-system, driver or hardware stability fix is claimed.

## Updating

Extract the new Windows ZIP into a fresh folder and run Dolly.exe. Python and Tcl/Tk are bundled. Keep the previous installation until your normal workflow is checked. The Source ZIP contains the complete source manifest for this version.
