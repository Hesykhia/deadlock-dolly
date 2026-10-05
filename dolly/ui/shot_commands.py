"""Shared shot-edit transactions; no Tk or engine access.

Desktop and native actions reach these through the same application adapters.
The caller owns prompts, publication, UI refresh and controller capture.
"""
import copy


def commit_camera(project, keys):
    candidate = copy.deepcopy(project)
    candidate.keyframes = sorted(keys, key=lambda key: key.time)
    if candidate.keyframes:
        candidate.validate()
    return candidate


def finish_capture(candidate, action, key, tick, selected=None):
    if action == "start":
        candidate.keyframes = [key]
        if tick is not None:
            candidate.start_tick = int(tick)
        candidate.interpolation = "spline"
    elif action == "replace":
        candidate.keyframes[selected] = key
    else:
        if any(existing.time == key.time for existing in candidate.keyframes):
            raise ValueError("This replay moment already has a view. Advance the replay, use Replace selected camera, "
                             "or choose Timed shot to add several views while paused.")
        candidate.keyframes.append(key)
    candidate.keyframes.sort(key=lambda item: item.time)
    candidate.validate()


def reset_rotation(keys, channel):
    keys = copy.deepcopy(keys)
    changed = False
    for key in keys:
        if getattr(key, "curve_" + channel) is not None:
            setattr(key, "curve_" + channel, None)
            changed = True
    return keys, changed


def reset_aspect(project, index):
    keys = copy.deepcopy(project.keyframes)
    keys[index].aspect_ratio = project.standard_aspect
    return keys


def selection_index(selected):
    return int(selected[0]) if selected else None


def move_history(redo, *, ready, sync, move, restore, empty):
    if not ready():
        return
    # Synchronize valid option edits before moving; no-op edits preserve Redo.
    sync()
    state = move(redo)
    if state is None:
        empty(redo)
        return
    restore(state, redo)
