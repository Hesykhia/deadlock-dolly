"""Audio profile reproducibility, operand masks, and shared module pins."""
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from generate_sound_profile import PROFILE, LEGACY_PROFILE, HEADER, emit_sound_header, build_sound_profile
from generate_profile import build_signature, ProfileError


class SoundProfileTests(unittest.TestCase):
    def test_generated_header_is_reproducible_without_game_binary(self):
        profile = json.loads(PROFILE.read_text())
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "sound.hpp"
            emit_sound_header(profile, output)
            self.assertEqual(output.read_bytes(), HEADER.read_bytes())

    def test_unreviewed_binary_cannot_generate_signatures_from_old_rvas(self):
        class Unknown:
            sha256 = "0" * 64
        with self.assertRaises(ProfileError):
            build_sound_profile(Unknown())

    def test_rip_displacement_before_immediate_and_short_jump_masks(self):
        try:
            import capstone
        except ImportError:
            self.skipTest("build-only capstone unavailable")
        class Image:
            base = 0x180000000
            def read(self, rva, length):
                return bytes.fromhex("c7 05 11 22 33 44 78 56 34 12 eb 05 e8 11 22 33 44")
        signature, mask = build_signature(Image(), 0, 17)
        self.assertEqual(mask, bytes([1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 1, 0, 0, 0, 0]))
        self.assertEqual(signature[6:10], bytes.fromhex("78 56 34 12"))

    def test_all_feature_pins_match_runtime_sources(self):
        from dolly import compatibility, preload
        modules = compatibility.load_manifest()["modules"]
        bridge = (ROOT / "native/src/bridge_win.cpp").read_text()
        for filename, constant, source in (
            ("scenesystem.dll", "kPlayerCaptureScenesystemHash", bridge),
            ("soundsystem.dll", "kSoundSystemHash", bridge),
            ("soundsystem.dll", "kSeptemberSoundSystemHash", bridge),
            ("scenesystem.dll", "kSeptemberScenesystemHash", bridge),
            ("rendersystemdx11.dll", "kRendererDiagnosticsHash",
             (ROOT / "native/include/dolly_renderer_diagnostics.hpp").read_text()),
        ):
            digest = re.search(constant + r'\[\]\s*=\s*"([a-f0-9]{64})"', source)[1]
            self.assertIn(digest, modules[f"bin/win64/{filename}"]["accepted"])
        sound = json.loads(PROFILE.read_text())
        legacy = json.loads(LEGACY_PROFILE.read_text())
        self.assertCountEqual(modules["bin/win64/soundsystem.dll"]["accepted"],
                              [legacy["sha256"], sound["sha256"]])
        self.assertEqual(modules["bin/win64/resourcesystem.dll"]["accepted"], [preload.RESOURCE_SHA256])
        client = modules["citadel/bin/win64/client.dll"]
        self.assertIn(preload.CLIENT_SHA256, client["accepted"])
        self.assertEqual(client["feature_pins"]["automatic preload"], [preload.CLIENT_SHA256])
        self.assertIn(preload.CLIENT_SHA256, (ROOT / "native/src/dolly_compat_generated.hpp").read_text())


if __name__ == "__main__":
    unittest.main()
