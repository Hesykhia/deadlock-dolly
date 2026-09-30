"""Deadlock-only audio capture and optional source-voice reconstruction."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace

from .runtime import resource_root


def _sample_window(offset: float, duration: float, available: int,
                   sample_rate: int = 48000) -> tuple[int, int]:
    """Require full reference coverage before writing or muxing clip audio."""
    if not math.isfinite(offset) or not math.isfinite(duration) or duration <= 0:
        raise RuntimeError("Video audio timing is invalid")
    start = round(offset * sample_rate)
    frames = round(duration * sample_rate)
    if offset < 0 or frames <= 0 or start + frames > available:
        raise RuntimeError("Game audio does not cover the complete video window; the silent video is kept")
    return start, frames


def _ffmpeg() -> Path:
    configured = os.environ.get("DOLLY_FFMPEG")
    if configured and Path(configured).is_file():
        return Path(configured)
    from .video_export import bundled_ffmpeg_path
    bundled = bundled_ffmpeg_path()
    if bundled is not None:
        return bundled
    found = shutil.which("ffmpeg")
    if found:
        return Path(found)
    try:
        import imageio_ffmpeg
        return Path(imageio_ffmpeg.get_ffmpeg_exe())
    except (ImportError, RuntimeError, OSError) as exc:
        raise RuntimeError("Audio export needs FFmpeg. Install imageio-ffmpeg or set DOLLY_FFMPEG.") from exc


def _viewer() -> Path:
    configured = os.environ.get("DOLLY_SOURCE2VIEWER")
    candidates = [Path(configured)] if configured else []
    found = shutil.which("Source2Viewer-CLI.exe")
    if found:
        candidates.append(Path(found))
    candidates.append(Path.home() / "Tools/ValveResourceFormat-20.0/Source2Viewer-CLI.exe")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise RuntimeError("Reconstructed audio needs Source2Viewer-CLI.exe. Set DOLLY_SOURCE2VIEWER to its path.")


def _mux(video: Path, audios: list[Path], ffmpeg: Path) -> None:
    if not audios:
        return
    with tempfile.TemporaryDirectory(prefix="dolly-mux-", dir=video.parent) as folder:
        target = Path(folder) / ("with_audio" + video.suffix)
        command = [str(ffmpeg), "-hide_banner", "-loglevel", "error", "-n",
                   "-i", str(video)]
        for audio in audios:
            command += ["-i", str(audio)]
        command += ["-map", "0:v:0"]
        for index in range(len(audios)):
            command += ["-map", f"{index + 1}:a:0"]
        command += ["-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", str(target)]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError("FFmpeg could not add clip audio: " + result.stderr[-1000:])
        if not target.is_file() or target.stat().st_size == 0:
            raise RuntimeError("FFmpeg did not produce the audio clip")
        os.replace(target, video)


class ClipAudioCapture:
    """Capture the game process and optional native voice log with video."""

    def __init__(self, video: Path, *, game_audio: bool, reconstructed: bool,
                 bridge, game: Path, game_pid: int):
        self.video = video
        self.game_audio = game_audio
        self.reconstructed = reconstructed
        self.bridge = bridge
        self.game = game
        self.game_pid = game_pid
        self.folder = video.with_name(video.stem + "_reconstructed")
        self.ffmpeg = _ffmpeg()
        self.viewer = _viewer() if reconstructed else None
        self.vpk = game.parents[2] / "citadel/pak01_dir.vpk"
        if reconstructed and not self.vpk.is_file():
            raise RuntimeError(f"Deadlock sound archive is missing: {self.vpk}")
        if reconstructed and self.folder.exists():
            raise FileExistsError(f"Reconstructed audio folder already exists: {self.folder}")
        self.recorder = resource_root() / "native/bin/win64/DollyGameAudio.exe"
        if not self.recorder.is_file():
            raise RuntimeError(f"Deadlock-only audio recorder is missing: {self.recorder}")
        if not isinstance(game_pid, int) or game_pid <= 0:
            raise RuntimeError("Deadlock is not running")
        self.temporary = tempfile.TemporaryDirectory(prefix="dolly-clip-audio-")
        self.work = Path(self.temporary.name)
        self.voice_log = self.work / "voices.csv"
        self.reference = self.work / "deadlock.wav"
        self.process = None
        self.voice_started = False

    def start(self) -> None:
        self.process = subprocess.Popen(
            [str(self.recorder), str(self.game_pid), str(self.reference)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if self.process.stdout.readline().strip() != "READY":
            detail = self.process.stderr.read() if self.process.poll() is not None else "No ready signal"
            self.cancel()
            raise RuntimeError(f"Deadlock audio capture could not start: {detail}")
        if self.reconstructed:
            try:
                self.bridge.start_source_audio(str(self.voice_log))
                self.voice_started = True
            except BaseException:
                self.cancel()
                raise

    def _end_capture(self) -> None:
        try:
            if self.voice_started:
                self.bridge.stop_source_audio()
                self.voice_started = False
        finally:
            if self.process:
                try:
                    _, stderr = self.process.communicate(input="\n", timeout=15)
                except subprocess.TimeoutExpired as exc:
                    self.process.kill()
                    self.process.communicate()
                    raise RuntimeError("Deadlock audio capture did not stop") from exc
                if self.process.returncode:
                    raise RuntimeError(f"Deadlock audio capture failed: {stderr.strip()}")

    def finish(self, video_status: dict) -> Path | None:
        import soundfile as sf

        self._end_capture()
        first_qpc = int(video_status.get("video_first_qpc", 0))
        frequency = int(video_status.get("qpc_frequency", 0))
        duration = float(video_status.get("duration", 0))
        if first_qpc <= 0 or frequency <= 0 or duration <= 0:
            raise RuntimeError("Video did not report its first frame clock and duration")
        clock = json.loads(Path(str(self.reference) + ".clock.json").read_text())
        origin = float(clock["first_sample_qpc_seconds"])
        offset = first_qpc / frequency - origin
        audio, rate = sf.read(self.reference, always_2d=True, dtype="float32")
        if rate != 48000 or audio.shape[1] != 2:
            raise RuntimeError("Game audio must be 48 kHz stereo")
        start, frames = _sample_window(offset, duration, len(audio), rate)
        metadata = {"first_block_end_monotonic": origin + 1024 / rate,
                    "loopback_block_frames": 1024, "video_first_qpc": first_qpc,
                    "qpc_frequency": frequency, "clip_offset_seconds": offset,
                    "duration_seconds": duration}
        self.reference.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n")
        tracks = []
        if self.game_audio:
            game_clip = self.video.with_name(self.video.stem + "_game_audio.wav")
            sf.write(game_clip, audio[start:start + frames], 48000, subtype="FLOAT")
            tracks.append(game_clip)
        if self.reconstructed:
            from tools.export_captured_audio import export
            from tools.filter_captured_audio_window import filter_window
            from tools.fit_reference_voices import fit

            filtered = self.work / "window_voices.csv"
            filter_window(self.voice_log, self.reference, filtered)
            sources = self.work / "sources"
            export(filtered, sources, vpk=self.vpk, viewer=self.viewer, ffmpeg=self.ffmpeg)
            state = Path(str(self.voice_log) + ".state.csv")
            if not state.is_file():
                raise RuntimeError("The native voice-state sidecar is missing")
            fitted = self.work / "fitted"
            fit(SimpleNamespace(source_dir=sources, reference_wav=self.reference,
                                reference_json=self.reference.with_suffix(".json"),
                                state_csv=state, output=fitted,
                                clip_offset=offset, clip_duration=duration, passes=8))
            self.folder.mkdir(parents=True)
            shutil.move(str(fitted / "sounds"), str(self.folder / "sounds"))
            shutil.move(str(fitted / "reconstructed.wav"), str(self.folder / "reconstructed.wav"))
            shutil.move(str(fitted / "fitted_usage.csv"), str(self.folder / "usage.csv"))
        _mux(self.video, tracks, self.ffmpeg)
        self.temporary.cleanup()
        return self.folder if self.reconstructed else None

    def cancel(self) -> None:
        try:
            if self.voice_started:
                self.bridge.stop_source_audio()
                self.voice_started = False
        finally:
            if self.process and self.process.poll() is None:
                self.process.kill()
                self.process.communicate()
            self.temporary.cleanup()
