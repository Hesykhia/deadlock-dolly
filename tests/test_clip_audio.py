"""Audio export runtime selection, independent of a running game."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from dolly.clip_audio import _ffmpeg, _sample_window


class AudioWindowTests(unittest.TestCase):
    def test_complete_window_uses_exact_sample_bounds(self):
        self.assertEqual(_sample_window(.5, 3, 168000), (24000, 144000))

    def test_missing_beginning_is_not_clamped_into_a_delayed_track(self):
        with self.assertRaisesRegex(RuntimeError, 'complete video window'):
            _sample_window(-.02, 3, 200000)

    def test_missing_tail_is_not_silently_muxed_with_shortest(self):
        with self.assertRaisesRegex(RuntimeError, 'complete video window'):
            _sample_window(.5, 3, 167999)

    def test_invalid_or_empty_timing_is_rejected(self):
        for offset, duration in ((float('nan'), 3), (0, float('inf')), (0, 0), (0, 1e-9)):
            with self.assertRaises(RuntimeError):
                _sample_window(offset, duration, 200000)


class AudioRuntimeTests(unittest.TestCase):
    def test_packaged_runtime_does_not_require_path_installation(self):
        bundled = Path('private-bundle/ffmpeg.exe')
        with patch.dict('os.environ', {}, clear=True), \
                patch('dolly.video_export.bundled_ffmpeg_path', return_value=bundled), \
                patch('dolly.clip_audio.shutil.which') as search:
            self.assertEqual(_ffmpeg(), bundled)
            search.assert_not_called()

    def test_explicit_configured_runtime_takes_precedence(self):
        with tempfile.TemporaryDirectory() as folder:
            configured = Path(folder)/'ffmpeg.exe'
            configured.write_bytes(b'MZ')
            with patch.dict('os.environ', {'DOLLY_FFMPEG':str(configured)}, clear=True), \
                    patch('dolly.video_export.bundled_ffmpeg_path') as bundled:
                self.assertEqual(_ffmpeg(), configured)
                bundled.assert_not_called()

    def test_path_fallback_is_retained_without_a_bundle(self):
        with patch.dict('os.environ', {}, clear=True), \
                patch('dolly.video_export.bundled_ffmpeg_path', return_value=None), \
                patch('dolly.clip_audio.shutil.which', return_value='custom/ffmpeg.exe'):
            self.assertEqual(_ffmpeg(), Path('custom/ffmpeg.exe'))
