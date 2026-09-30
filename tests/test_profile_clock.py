import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
import generate_profile


class ProfileClockTests(unittest.TestCase):
    def setUp(self):
        self.profile = json.loads((TOOLS.parent / "native/profiles/deadlock-2026-09-11b-complete.json").read_text())

    def test_exact_review_enables_render_fraction(self):
        self.assertEqual(generate_profile.reviewed_render_fraction(self.profile["client"]), 0x38)

    def test_unreviewed_profile_keeps_legacy_clock(self):
        self.profile["client"]["globals"].pop("replay_clock_review")
        self.assertEqual(generate_profile.reviewed_render_fraction(self.profile["client"]), 0)

    def test_carried_review_does_not_authorize_new_game_hash(self):
        self.profile["client"]["client_sha256"] = "0" * 64
        self.assertEqual(generate_profile.reviewed_render_fraction(self.profile["client"]), 0)

    def test_unknown_fraction_layout_is_rejected(self):
        self.profile["client"]["globals"]["replay_clock_review"]["render_fraction_offset"] = "0x3c"
        with self.assertRaises(ValueError):
            generate_profile.reviewed_render_fraction(self.profile["client"])

    def test_header_emits_reviewed_and_unreviewed_offsets(self):
        changed = copy.deepcopy(self.profile)
        changed["client"]["client_sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "profile.hpp"
            generate_profile.emit_header([(self.profile, None), (changed, None)], out)
            rows = [line for line in out.read_text().splitlines() if line.lstrip().startswith('{ "')]
        self.assertEqual(len(rows), 2)
        self.assertIn("0x38, nullptr, nullptr, 0", rows[0])
        self.assertIn("0x0, nullptr, nullptr, 0", rows[1])


class UpdatedCameraProfileTests(unittest.TestCase):
    def setUp(self):
        self.profile = json.loads((TOOLS.parent / "native/profiles/deadlock-2026-09-29-complete.json").read_text())

    def test_updated_layout_requires_the_reviewed_hash(self):
        self.assertEqual(generate_profile.reviewed_camera_layout(self.profile["client"]), 1)
        self.profile["client"]["client_sha256"] = "0" * 64
        with self.assertRaises(generate_profile.ProfileError):
            generate_profile.reviewed_camera_layout(self.profile["client"])

    def test_layout_revision_cannot_silently_move_a_field(self):
        for field in ("aspect_offset", "view_flag_byte_offset", "auxiliary_origin_offset",
                      "auxiliary_angles_offset", "extra_origin_offset"):
            client = copy.deepcopy(self.profile["client"])
            client[field] = "0x500"
            with self.subTest(field=field), self.assertRaises(generate_profile.ProfileError):
                generate_profile.reviewed_camera_layout(client)

    def test_new_wrapper_is_exact_only_and_has_its_own_prologue(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "profile.hpp"
            # A supplied image cannot accidentally enable the legacy AOB path.
            generate_profile.emit_header([(self.profile, {"image": object(),
                "setup_rva": 0x1897760, "caller_rva": 0x1890d14})], out)
            header = out.read_text()
        self.assertIn("nullptr, nullptr, 0, 1, 0x5cf000", header)
        self.assertIn("0x48,0x89,0x5c,0x24,0x08", header)
        self.assertNotIn("kSignature0[]", header)

    def test_old_signature_survives_replacement_of_installed_binary(self):
        old = json.loads((TOOLS.parent / "native/profiles/deadlock-2026-09-25-complete.json").read_text())
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "profile.hpp"
            generate_profile.emit_header([(old, None)], out)
            self.assertIn("kSignature0[]", out.read_text())
            old["client"]["camera_signature"]["client_sha256"] = "0" * 64
            with self.assertRaises(generate_profile.ProfileError):
                generate_profile.emit_header([(old, None)], out)

    def test_review_cannot_be_reused_for_another_image(self):
        class ChangedImage:
            sha256 = "0" * 64
        with self.assertRaisesRegex(generate_profile.ProfileError, "new exact-build review"):
            generate_profile.build_profile(ChangedImage(), None, None, self.profile, "future")

    def test_wrapper_review_rejects_changed_engine_or_tier0(self):
        from types import SimpleNamespace
        client = SimpleNamespace(sha256=self.profile["client"]["client_sha256"])
        engine = SimpleNamespace(sha256=self.profile["engine"]["sha256"],
                                 image_size=int(self.profile["engine"]["image_size"], 16))
        tier0 = SimpleNamespace(sha256=self.profile["tier0"]["sha256"],
                                image_size=int(self.profile["tier0"]["size_of_image"], 16))
        for role, image in (("engine", engine), ("tier0", tier0)):
            for field, changed in (("sha256", "0" * 64), ("image_size", 1)):
                before = getattr(image, field)
                setattr(image, field, changed)
                with self.subTest(role=role, field=field), self.assertRaisesRegex(
                        generate_profile.ProfileError, role + " requires a new exact-build review"):
                    generate_profile.build_profile(client, engine, tier0, self.profile, "future")
                setattr(image, field, before)
