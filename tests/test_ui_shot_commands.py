"""Shared camera-edit transactions, independent of widgets and engine state."""
import copy
import unittest
from unittest.mock import Mock

from dolly.path import Keyframe, Project
from dolly.ui import shot_commands as commands


def key(time):
    return Keyframe(time, 1, 2, 3, 4, 5, 6)


class ShotCommandTests(unittest.TestCase):
    def test_camera_commit_sorts_private_candidate_and_does_not_publish_on_failure(self):
        original = Project(name='Shot', keyframes=[key(0)])
        candidate = commands.commit_camera(original, [key(2), key(0)])
        self.assertEqual([k.time for k in candidate.keyframes], [0, 2])
        self.assertEqual(len(original.keyframes), 1)
        self.assertIsNot(candidate, original)
        with self.assertRaises(ValueError): commands.commit_camera(original, [key(0), key(0)])
        self.assertEqual(len(original.keyframes), 1)

    def test_start_replace_and_duplicate_capture_match_existing_transactions(self):
        project = Project(name='Shot', keyframes=[key(1)])
        commands.finish_capture(project, 'start', key(0), 123)
        self.assertEqual(project.start_tick, 123)
        self.assertEqual(project.interpolation, 'spline')
        replacement = key(0); replacement.x = 42
        commands.finish_capture(project, 'replace', replacement, None, 0)
        self.assertEqual(project.keyframes[0].x, 42)
        before = copy.deepcopy(project)
        with self.assertRaisesRegex(ValueError, 'This replay moment already has a view'):
            commands.finish_capture(project, 'append', key(0), None)
        self.assertEqual(project, before)

    def test_curve_and_aspect_resets_keep_original_keys_and_other_fields(self):
        project = Project(name='Shot', keyframes=[key(0)])
        project.keyframes[0].curve_yaw = 77
        project.keyframes[0].curve_pitch = 33
        keys, changed = commands.reset_rotation(project.keyframes, 'yaw')
        self.assertTrue(changed); self.assertIsNone(keys[0].curve_yaw)
        self.assertEqual(keys[0].curve_pitch, 33)
        self.assertEqual(project.keyframes[0].curve_yaw, 77)
        keys2, changed2 = commands.reset_rotation(keys, 'yaw')
        self.assertFalse(changed2)
        project.keyframes[0].aspect_ratio = 2.0
        reset = commands.reset_aspect(project, 0)
        self.assertEqual(reset[0].aspect_ratio, project.standard_aspect)
        self.assertEqual(project.keyframes[0].aspect_ratio, 2.0)

    def test_history_checks_ready_then_syncs_before_move_and_restore(self):
        order = []; state = object()
        commands.move_history(True, ready=lambda: True,
            sync=lambda: order.append('sync'),
            move=lambda redo: (order.append(('move', redo)), state)[1],
            restore=lambda found, redo: order.append(('restore', found, redo)), empty=Mock())
        self.assertEqual(order, ['sync', ('move', True), ('restore', state, True)])
        sync, move, restore, empty = Mock(), Mock(return_value=None), Mock(), Mock()
        commands.move_history(False, ready=lambda: False, sync=sync, move=move, restore=restore, empty=empty)
        for call in (sync, move, restore, empty): call.assert_not_called()
        commands.move_history(False, ready=lambda: True, sync=sync, move=move, restore=restore, empty=empty)
        empty.assert_called_once_with(False); restore.assert_not_called()

    def test_selection_preserves_empty_and_numeric_tree_ids(self):
        self.assertIsNone(commands.selection_index(()))
        self.assertEqual(commands.selection_index(('3',)), 3)
        with self.assertRaises(ValueError): commands.selection_index(('not-an-index',))
