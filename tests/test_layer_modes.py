"""Layer isolation commands and take scheduling without a live game."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from dolly.controller import Controller
from dolly.video_export import VideoOptions


CLASSES = ("EnvMap", "BarnLight", "DirectionalLight", "OmniLight",
           "panorama_world_panel", "LightProbeVolume", "SkinnedObject", "Default",
           "MeshBuilderObject", "ZipLineRopeSegment", "ParticleSystem",
           "InstancedMesh", "AggregateDesc", "Skybox", "projectedDecal")


class LayerModeTests(unittest.TestCase):
    def setUp(self):
        self.controller = Controller()
        self.commands = []
        self.classes = CLASSES
        self.controller._request = self.request

    def request(self, command, **kwargs):
        self.commands.append(command)
        if command == "sc_showclasses":
            return "\n".join(f"{name}    Hide DebugLevel: 0 1 2 3" for name in self.classes)
        if command in Controller.MATTE_CVARS:
            return f"{command} = 1"
        return ""

    def test_matte_layer_disables_and_restores_post_processing(self):
        self.controller.begin_matte_layer()
        self.assertEqual(self.commands[-1],
                         "r_effects_bloom 0; r_post_bloom 0; r_post_bloom_strength 0")
        self.controller.end_matte_layer()
        self.assertEqual(self.commands[-1],
                         "r_effects_bloom 1; r_post_bloom 1; r_post_bloom_strength 1")

    def test_matte_layer_ignores_missing_cvars(self):
        original = self.request

        def missing(command):
            if command in Controller.MATTE_CVARS:
                raise RuntimeError("unknown command")
            return original(command)

        self.controller._request = missing
        self.controller.begin_matte_layer()
        self.controller.end_matte_layer()

    def hide_commands(self):
        return [command for command in self.commands if command.endswith(" 8")]

    def reset_commands(self):
        return [command for command in self.commands if command.endswith(" 0")]

    def test_world_mode_shows_world_classes_and_hides_characters_effects_and_ui(self):
        applied = self.controller.apply_layer_mode("world")
        world_keep = set(Controller.LAYER_MODES["world"]["keep"])
        world_keep.update(Controller.LAYER_MODES["world"]["optional_keep"])
        # World keeps the world/light/geometry classes and hides everything else
        # (characters, effects and any class not in the keep-list).
        self.assertEqual(sorted(applied["hidden"]),
                         sorted(name for name in CLASSES if name not in world_keep))
        self.assertIn("sc_setclassflags SkinnedObject 8", self.commands)
        self.assertIn("sc_setclassflags ParticleSystem 8", self.commands)
        self.assertNotIn("sc_setclassflags AggregateDesc 8", self.commands)
        self.assertNotIn("sc_setclassflags Default 8", self.commands)
        self.assertEqual(len(self.reset_commands()), len(CLASSES))

    def test_players_mode_keeps_only_skinned_objects(self):
        applied = self.controller.apply_layer_mode("players")
        self.assertEqual(sorted(applied["hidden"]),
                         sorted(name for name in CLASSES if name != "SkinnedObject"))
        self.assertEqual(len(self.hide_commands()), len(applied["hidden"]))
        self.assertNotIn("sc_setclassflags SkinnedObject 8", self.commands)
        # A previous layer's flags are cleared before the new layer is set.
        self.assertEqual(len(self.reset_commands()), len(CLASSES))

    def test_effects_mode_keeps_only_the_particle_system(self):
        applied = self.controller.apply_layer_mode("effects")
        self.assertEqual(sorted(applied["hidden"]),
                         sorted(name for name in CLASSES if name != "ParticleSystem"))
        self.assertEqual(len(self.hide_commands()), len(applied["hidden"]))
        self.assertNotIn("sc_setclassflags ParticleSystem 8", self.commands)
        self.assertEqual(len(self.reset_commands()), len(CLASSES))

    def test_missing_required_class_fails_instead_of_wrong_layer(self):
        self.classes = tuple(name for name in CLASSES if name != "ParticleSystem")
        with self.assertRaisesRegex(RuntimeError, "ParticleSystem"):
            self.controller.apply_layer_mode("effects")

    def test_missing_required_world_class_fails_instead_of_wrong_layer(self):
        self.classes = tuple(name for name in CLASSES if name != "AggregateDesc")
        with self.assertRaisesRegex(RuntimeError, "AggregateDesc"):
            self.controller.apply_layer_mode("world")

    def test_current_registry_without_legacy_world_classes_is_supported(self):
        self.classes = tuple(name for name in CLASSES
                             if name not in ('DirectionalLight', 'projectedDecal')) + ('ShadowDecal',)
        applied = self.controller.apply_layer_mode('world')
        self.assertIn('SkinnedObject', applied['hidden'])
        self.assertIn('ShadowDecal', applied['hidden'])
        self.assertNotIn('AggregateDesc', applied['hidden'])
        self.controller.reset_layer_modes()
        self.assertFalse(self.controller._layer_hidden)

    def test_present_legacy_world_classes_remain_visible(self):
        self.controller.apply_layer_mode('world')
        self.assertNotIn('sc_setclassflags DirectionalLight 8', self.commands)
        self.assertNotIn('sc_setclassflags projectedDecal 8', self.commands)

    def test_unknown_registry_class_is_hidden_by_default(self):
        # A dynamic registry can add classes; the keep-list hides them so they
        # cannot silently leak into a layer.
        self.classes = CLASSES + ("futureNewClass",)
        applied = self.controller.apply_layer_mode("world")
        self.assertIn("futureNewClass", applied["hidden"])
        self.assertIn("sc_setclassflags futureNewClass 8", self.commands)

    def test_a_class_that_cannot_be_set_fails_the_mode(self):
        original = self.request

        def failing(command):
            if command == "sc_setclassflags ParticleSystem 8":
                raise RuntimeError("console busy")
            return original(command)

        self.controller._request = failing
        with self.assertRaisesRegex(RuntimeError, "ParticleSystem"):
            self.controller.apply_layer_mode("world")

    def test_unknown_mode_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown layer mode"):
            self.controller.apply_layer_mode("hud")

    def test_reset_restores_every_reported_class(self):
        # With no layer applied, reset restores the live registry.
        self.controller.reset_layer_modes()
        self.assertEqual(sorted(self.reset_commands()),
                         sorted("sc_setclassflags " + name + " 0" for name in CLASSES))

    def test_reset_after_a_layer_restores_only_what_was_hidden(self):
        applied = self.controller.apply_layer_mode("world")
        self.commands.clear()
        self.controller.reset_layer_modes()
        self.assertEqual(sorted(self.reset_commands()),
                         sorted("sc_setclassflags " + name + " 0"
                                for name in applied["hidden"]))


class LayerOptionsTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "shot.mp4"
        exe = Path(self.folder.name) / "ffmpeg.exe"
        exe.write_bytes(b"MZ")
        self.exe = exe

    def test_layers_require_fixed_step_and_unique_known_names(self):
        with self.assertRaisesRegex(ValueError, "Fixed-step"):
            VideoOptions(self.path, layers=("world",), ffmpeg_path=self.exe).validated()
        with self.assertRaisesRegex(ValueError, "Unknown layer"):
            VideoOptions(self.path, fixed_step=True, layers=("hud",),
                         ffmpeg_path=self.exe).validated()
        with self.assertRaisesRegex(ValueError, "once"):
            VideoOptions(self.path, fixed_step=True, layers=("world", "world"),
                         ffmpeg_path=self.exe).validated()
        with self.assertRaisesRegex(ValueError, "tuple"):
            VideoOptions(self.path, fixed_step=True, layers=["world"],
                         ffmpeg_path=self.exe).validated()

    def test_layers_need_an_ffmpeg_encoder_for_the_alpha_matte(self):
        with self.assertRaisesRegex(ValueError, "FFmpeg encoder"):
            VideoOptions(self.path, fixed_step=True, layers=("players",),
                         codec="builtin").validated()

    def test_layers_use_the_take_folder_layout(self):
        options = VideoOptions(self.path, fixed_step=True, layers=("world", "players"),
                               ffmpeg_path=self.exe).validated()
        self.assertEqual(options.layers, ("world", "players"))
        self.assertFalse(options.depth)

    def test_existing_take_folder_is_rejected_for_layer_only_takes(self):
        self.path.with_suffix("").mkdir()
        with self.assertRaisesRegex(ValueError, "folder"):
            VideoOptions(self.path, fixed_step=True, layers=("world",),
                         ffmpeg_path=self.exe).validated()


if __name__ == "__main__":
    unittest.main()
