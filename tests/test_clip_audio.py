"""Audio export runtime selection, independent of a running game."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from dolly.clip_audio import _ffmpeg, _mux, _sample_window


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


class AudioMuxEnvironmentTests(unittest.TestCase):
    """The muxer launches FFmpeg like the other encoders: clean env, no console."""

    def test_mux_uses_external_environment_without_a_window(self):
        from contextlib import contextmanager
        from types import SimpleNamespace
        seen = {}

        @contextmanager
        def environment():
            seen["entered"] = True
            yield {"PATH": "clean"}

        def spawn(command, **kwargs):
            seen.update(kwargs)
            Path(command[-1]).write_bytes(b"audio")
            return SimpleNamespace(returncode=0, stderr="")

        with tempfile.TemporaryDirectory() as folder:
            video = Path(folder) / "video.mp4"
            video.write_bytes(b"video")
            audio = Path(folder) / "audio.wav"
            audio.write_bytes(b"audio")
            with patch("dolly.clip_audio.external_program_environment", environment), \
                    patch("dolly.clip_audio.subprocess.run", spawn):
                _mux(video, [audio], Path("ffmpeg.exe"))
        self.assertTrue(seen["entered"])
        self.assertEqual(seen["env"], {"PATH": "clean"})
        self.assertEqual(seen["creationflags"], getattr(subprocess, "CREATE_NO_WINDOW", 0))


class AudioMuxFrameTests(unittest.TestCase):
    def test_audio_rounding_does_not_remove_last_video_frame(self):
        # Exercise the shipped muxer and decode both files; a command-string
        # assertion would not catch packet loss at the end of the container.
        from dolly.video_export import bundled_ffmpeg_path
        ffmpeg = bundled_ffmpeg_path()
        if ffmpeg is None:
            self.skipTest("Bundled FFmpeg is unavailable")
        with tempfile.TemporaryDirectory() as folder:
            video = Path(folder) / "video.mp4"
            audio = Path(folder) / "audio.wav"
            def run(*args):
                return subprocess.run(
                    [str(ffmpeg), "-hide_banner", "-loglevel", "error", *args],
                    check=True, capture_output=True).stdout
            run("-f", "lavfi", "-i", "testsrc2=size=64x64:rate=60",
                "-frames:v", "60", "-c:v", "mpeg4", "-bf", "0", str(video))
            run("-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000",
                "-t", "0.999", "-ac", "2", str(audio))
            def decoded_frames():
                data = run("-i", str(video), "-map", "0:v:0", "-f", "framemd5", "-")
                return [line for line in data.splitlines() if not line.startswith(b"#")]
            before = decoded_frames()
            self.assertEqual(len(before), 60)
            _mux(video, [audio], ffmpeg)
            self.assertEqual(decoded_frames(), before)
