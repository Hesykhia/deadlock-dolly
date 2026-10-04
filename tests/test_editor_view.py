"""Native editor projection accepts plain inputs and preserves last-valid values."""
import unittest
from dolly import editor_view as view


class EditorViewTests(unittest.TestCase):
    def test_incomplete_playback_keeps_cached_values_without_mutating_cache(self):
        previous = {'playback_speed': 2.0, 'playback_rate': 120}
        self.assertEqual(view.playback_values(view.EditorControls(speed='-', rate=''), previous), (2.0, 120))
        self.assertEqual(previous, {'playback_speed': 2.0, 'playback_rate': 120})
        self.assertEqual(view.playback_values(view.EditorControls(speed='.05', rate='30'), previous), (.05, 30))

    def test_video_fallback_and_depth_exr_dependency_are_preserved(self):
        previous = {'video_fps': 120, 'video_speed': 2, 'video_bitrate_mbps': 40,
                    'video_fixed_step': True, 'video_depth': True, 'video_depth_exr': True}
        values = view.video_values(view.EditorControls(video_fps='nan', video_bitrate='invalid',
            video_export_speed='-', video_depth=False), previous)
        self.assertEqual(values, (120, 40, 0, True, 2, False, False))
        self.assertEqual(view.video_values(view.EditorControls())[0], 60)

    def test_field_read_errors_follow_original_validation_policy(self):
        problem = ValueError('unfinished')
        self.assertEqual(view.playback_values(view.EditorControls(speed=view.ReadError(problem))), (1.0, 60))
        self.assertEqual(view.pov_duration(view.EditorControls(video_pov_duration=view.ReadError(problem)),
                                          {'pov_duration': 7}), 7)
        with self.assertRaisesRegex(ValueError, 'unfinished'):
            view.video_values(view.EditorControls(video_fixed_step=view.ReadError(problem)))

    def test_pov_duration_range_and_last_valid_fallback(self):
        for invalid in ('', 'nan', '.09', '121'):
            with self.subTest(value=invalid):
                self.assertEqual(view.pov_duration(view.EditorControls(video_pov_duration=invalid), {'pov_duration': 3}), 3)
        self.assertEqual(view.pov_duration(view.EditorControls(video_pov_duration='120')), 120)

    def test_projection_and_picker_import_without_coordinator_or_publication(self):
        import subprocess
        import sys
        result = subprocess.run([sys.executable, '-c',
            'import sys; from dolly import editor_view, bone_picker; '
            'forbidden={"dolly.editor_session", "dolly.editor_publication", "dolly.editor_dispatch", "dolly.gui"}; '
            'assert not forbidden.intersection(sys.modules), sorted(forbidden.intersection(sys.modules))'],
            capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
