"""The bundled ReShade library must merge into Dolly's private config safely."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dolly import reshade_setup


class RuntimeIssueTests(unittest.TestCase):
    def test_missing_runtime_names_the_path_and_the_fact_dolly_never_deletes_it(self):
        with tempfile.TemporaryDirectory() as folder:
            missing = Path(folder) / "Dolly-ReShade" / "ReShade64.dll"
            issue = reshade_setup.runtime_issue(missing)
        self.assertIsNotNone(issue)
        self.assertIn("missing", issue)
        self.assertIn(str(missing), issue)
        self.assertIn("never", issue)

    def test_runtime_inside_the_dolly_folder_warns_about_updates(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "DeadlockDolly"
            runtime = root / "_internal" / "ReShade64.dll"
            runtime.parent.mkdir(parents=True)
            runtime.write_bytes(b"MZ")
            issue = reshade_setup.runtime_issue(runtime, application_root=root)
        self.assertIsNotNone(issue)
        self.assertIn("inside the Dolly folder", issue)
        self.assertIn("Dolly-ReShade", issue)

    def test_runtime_in_its_own_folder_is_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "DeadlockDolly"
            runtime = Path(folder) / "Dolly-ReShade" / "ReShade64.dll"
            runtime.parent.mkdir(parents=True)
            runtime.write_bytes(b"MZ")
            self.assertIsNone(reshade_setup.runtime_issue(runtime, application_root=root))


class LibraryChoiceTests(unittest.TestCase):
    def _chosen(self, temp: Path) -> Path:
        shaders = temp / "reshade-shaders" / "Shaders"
        textures = temp / "reshade-shaders" / "Textures"
        shaders.mkdir(parents=True)
        textures.mkdir(parents=True)
        (shaders / "LUT.fx").write_text("technique LUT { }\n", encoding="utf-8")
        return shaders.parent

    def test_library_issue_accepts_the_folder_or_its_shaders_subfolder(self):
        with tempfile.TemporaryDirectory() as folder:
            chosen = self._chosen(Path(folder))
            self.assertIsNone(reshade_setup.library_issue(chosen))
            self.assertIsNone(reshade_setup.library_issue(chosen / "Shaders"))

    def test_library_issue_reports_a_missing_or_effectless_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            temp = Path(folder)
            missing = temp / "gone"
            issue = reshade_setup.library_issue(missing)
            self.assertIn("missing", issue)
            empty = temp / "empty"
            empty.mkdir()
            issue = reshade_setup.library_issue(empty)
            self.assertIn(".fx", issue)

    def test_library_paths_find_shaders_and_sibling_textures(self):
        with tempfile.TemporaryDirectory() as folder:
            chosen = self._chosen(Path(folder))
            shaders, textures = reshade_setup.library_paths(chosen)
            self.assertEqual(shaders, chosen / "Shaders")
            self.assertEqual(textures, chosen / "Textures")
            picked, _ = reshade_setup.library_paths(chosen / "Shaders")
            self.assertEqual(picked, chosen / "Shaders")

class PrepareConfigTests(unittest.TestCase):
    def _paths(self, temp: Path):
        base = temp / "bundle" / "third_party" / "reshade_shaders"
        shaders = base / "Shaders"
        textures = base / "Textures"
        preset = temp / "bundle" / "presets" / reshade_setup.PRESET_NAME
        shaders.mkdir(parents=True)
        textures.mkdir(parents=True)
        preset.parent.mkdir(parents=True)
        preset.write_text("Techniques=\n", encoding="utf-8")
        return shaders, textures, preset

    def _chosen(self, temp: Path) -> Path:
        shaders = temp / "reshade-shaders" / "Shaders"
        textures = temp / "reshade-shaders" / "Textures"
        shaders.mkdir(parents=True)
        textures.mkdir(parents=True)
        (shaders / "LUT.fx").write_text("technique LUT { }\n", encoding="utf-8")
        return shaders.parent

    def test_merges_a_chosen_library(self):
        with tempfile.TemporaryDirectory() as folder:
            temp = Path(folder)
            shaders, textures, preset = self._paths(temp)
            chosen = self._chosen(temp)
            config = temp / "ReShade.ini"
            with patch.object(reshade_setup, "bundled_shader_paths", return_value=(shaders, textures)), \
                 patch.object(reshade_setup, "bundled_preset", return_value=preset):
                summary = reshade_setup.prepare_config(config, library_root=chosen)
            text = config.read_text(encoding="utf-8")
            self.assertEqual(summary["library_shaders"], chosen / "Shaders")
            self.assertEqual(summary["library_textures"], chosen / "Textures")
            self.assertIn(str(shaders), text)
            self.assertIn(str(chosen / "Shaders"), text)
            self.assertIn(str(chosen / "Textures"), text)

    def test_chosen_library_replaces_a_missing_bundled_one(self):
        with tempfile.TemporaryDirectory() as folder:
            temp = Path(folder)
            shaders = temp / "Shaders"
            shaders.mkdir()
            (shaders / "Custom.fx").write_text("technique Custom { }\n", encoding="utf-8")
            config = temp / "ReShade.ini"
            with patch.object(reshade_setup, "bundled_shader_paths", return_value=(None, None)), \
                 patch.object(reshade_setup, "bundled_preset", return_value=None):
                summary = reshade_setup.prepare_config(config, library_root=shaders)
            text = config.read_text(encoding="utf-8")
            self.assertTrue(summary["changed"])
            self.assertIn(f"EffectSearchPaths={shaders}", text)

    def test_merges_paths_and_fills_missing_preset(self):
        with tempfile.TemporaryDirectory() as folder:
            temp = Path(folder)
            shaders, textures, preset = self._paths(temp)
            config = temp / "ReShade.ini"
            config.write_text(
                "[GENERAL]\n"
                "EffectSearchPaths=C:\\mine\\Shaders\n"
                "PerformanceMode=1\n"
                "\n"
                "[INPUT]\n"
                "InputProcessing=2\n",
                encoding="utf-8",
            )
            with patch.object(reshade_setup, "bundled_shader_paths", return_value=(shaders, textures)), \
                 patch.object(reshade_setup, "bundled_preset", return_value=preset):
                summary = reshade_setup.prepare_config(config)
            text = config.read_text(encoding="utf-8")
            self.assertTrue(summary["changed"])
            self.assertIn(f"EffectSearchPaths=C:\\mine\\Shaders,{shaders}", text)
            self.assertIn(f"TextureSearchPaths={textures}", text)
            self.assertIn(f"PresetPath={config.parent / 'presets' / preset.name}", text)
            self.assertEqual(summary["preset"].read_bytes(), preset.read_bytes())
            self.assertIn("PerformanceMode=1", text)
            self.assertIn("InputProcessing=2", text)
            self.assertIn("[INPUT]", text)

    def test_keeps_user_preset_and_does_not_duplicate_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            temp = Path(folder)
            shaders, textures, preset = self._paths(temp)
            mine = temp / "MyPreset.ini"
            mine.write_text("Techniques=\n", encoding="utf-8")
            config = temp / "ReShade.ini"
            config.write_text(
                "[GENERAL]\n"
                f"EffectSearchPaths={shaders}\n"
                f"TextureSearchPaths={textures}\n"
                f"PresetPath={mine}\n",
                encoding="utf-8",
            )
            with patch.object(reshade_setup, "bundled_shader_paths", return_value=(shaders, textures)), \
                 patch.object(reshade_setup, "bundled_preset", return_value=preset):
                summary = reshade_setup.prepare_config(config)
            text = config.read_text(encoding="utf-8")
            self.assertFalse(summary["changed"])
            self.assertIn(f"PresetPath={mine}", text)
            self.assertNotIn("PresetPath=" + str(preset), text)
            self.assertEqual(text.count(str(shaders)), 1)
            self.assertEqual(text.count(str(textures)), 1)

    def test_missing_library_is_a_noop(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / "ReShade.ini"
            with patch.object(reshade_setup, "bundled_shader_paths", return_value=(None, None)), \
                 patch.object(reshade_setup, "bundled_preset", return_value=None):
                summary = reshade_setup.prepare_config(config)
            self.assertFalse(summary["changed"])
            self.assertFalse(config.exists())

    def test_missing_config_is_created(self):
        with tempfile.TemporaryDirectory() as folder:
            temp = Path(folder)
            shaders, textures, preset = self._paths(temp)
            config = temp / "nested" / "ReShade.ini"
            with patch.object(reshade_setup, "bundled_shader_paths", return_value=(shaders, textures)), \
                 patch.object(reshade_setup, "bundled_preset", return_value=preset):
                summary = reshade_setup.prepare_config(config)
            text = config.read_text(encoding="utf-8")
            self.assertTrue(summary["changed"])
            self.assertIn("[GENERAL]", text)
            self.assertIn(f"EffectSearchPaths={shaders}", text)
            self.assertIn(f"PresetPath={config.parent / 'presets' / preset.name}", text)

    def test_preserves_user_preset_edits_and_binary_newlines(self):
        with tempfile.TemporaryDirectory() as folder:
            temp = Path(folder)
            shaders, textures, preset = self._paths(temp)
            config = temp / "ReShade.ini"
            config.write_bytes(b"\xef\xbb\xbf[GENERAL]\r\nPerformanceMode=0\r\n")
            with patch.object(reshade_setup, "bundled_shader_paths", return_value=(shaders, textures)), \
                 patch.object(reshade_setup, "bundled_preset", return_value=preset):
                result = reshade_setup.prepare_config(config)
                result["preset"].write_text("Techniques=MyCustomLook\n", encoding="utf-8")
                first = config.read_bytes()
                self.assertFalse(reshade_setup.prepare_config(config)["changed"])
                self.assertEqual(config.read_bytes(), first)
                self.assertNotIn(b"\r\r\n", first)
                self.assertTrue(first.startswith(b"\xef\xbb\xbf"))
                self.assertEqual(result["preset"].read_text(), "Techniques=MyCustomLook\n")

    def test_windows_path_case_and_key_spacing_do_not_duplicate_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / "ReShade.ini"
            config.write_text("[GENERAL]\nEffectSearchPaths = C:\\Shaders\nPresetPath = MyLook.ini\n")
            with patch.object(reshade_setup, "bundled_shader_paths", return_value=(Path("c:/shaders"), None)), \
                 patch.object(reshade_setup, "bundled_preset", return_value=None):
                reshade_setup.prepare_config(config)
            text = config.read_text()
            self.assertEqual(text.count("EffectSearchPaths"), 1)
            field = next(line for line in text.splitlines() if line.startswith("EffectSearchPaths="))
            self.assertEqual(field.split("=", 1)[1].strip(), "C:\\Shaders")
            self.assertIn("PresetPath = MyLook.ini", text)

    def test_source_release_contains_the_library_and_default_techniques_exist(self):
        import re
        root = Path(__file__).resolve().parents[1]
        shipped = set((root / "SOURCE_FILES.txt").read_text().splitlines())
        library = root / "third_party/reshade_shaders"
        for path in library.rglob("*"):
            if path.is_file():
                self.assertIn(path.relative_to(root).as_posix(), shipped)
                self.assertNotEqual(path.suffix.lower(), ".dll")
        preset = root / "assets/reshade" / reshade_setup.PRESET_NAME
        self.assertIn(preset.relative_to(root).as_posix(), shipped)
        for line in preset.read_text().splitlines():
            if line.startswith(("Techniques=", "TechniqueSorting=")):
                for item in line.split("=", 1)[1].split(","):
                    name, file = item.split("@")
                    source = (library / "Shaders" / file).read_text(encoding="utf-8-sig")
                    self.assertRegex(source, r"\btechnique\s+" + re.escape(name) + r"\b")

    def test_merge_path_list_dedupes(self):
        result = reshade_setup.merge_path_list("a,b", [Path("b"), Path("c")])
        self.assertEqual(result, "a,b,c")

    def test_merge_path_list_collapses_existing_duplicates(self):
        result = reshade_setup.merge_path_list("C:\\Shaders,c:\\shaders ,C:\\Shaders", [])
        self.assertEqual(result, "C:\\Shaders")

    def test_merge_path_list_replaces_a_stale_bundled_library(self):
        old = "C:\\OldDolly\\_internal\\third_party\\reshade_shaders\\Shaders"
        current = Path("C:/NewDolly/_internal/third_party/reshade_shaders/Shaders")
        result = reshade_setup.merge_path_list(old, [current])
        self.assertEqual(result, str(current))

    def test_merge_path_list_keeps_unrelated_reshade_named_folders(self):
        other = "C:\\Mine\\reshade_shaders\\Custom"
        result = reshade_setup.merge_path_list(other, [Path("C:/Dolly/third_party/reshade_shaders/Shaders")])
        self.assertEqual(result, other + "," + str(Path("C:/Dolly/third_party/reshade_shaders/Shaders")))

    def test_prepare_config_replaces_three_stale_library_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            temp = Path(folder)
            shaders, textures, preset = self._paths(temp)
            stale = "C:\\Old\\third_party\\reshade_shaders\\{}"
            config = temp / "ReShade.ini"
            config.write_text(
                "[GENERAL]\n"
                f"EffectSearchPaths={stale.format('Shaders')},{stale.format('Shaders').replace('C:', 'D:')}\n"
                f"TextureSearchPaths={stale.format('Textures')}\n",
                encoding="utf-8",
            )
            with patch.object(reshade_setup, "bundled_shader_paths", return_value=(shaders, textures)), \
                 patch.object(reshade_setup, "bundled_preset", return_value=preset):
                reshade_setup.prepare_config(config)
            text = config.read_text(encoding="utf-8")
            self.assertNotIn("Old", text)
            self.assertEqual(text.count(str(shaders)), 1)
            self.assertEqual(text.count(str(textures)), 1)


if __name__ == "__main__":
    unittest.main()
