"""Audio export runtime selection, independent of a running game."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from dolly.clip_audio import _ffmpeg


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
