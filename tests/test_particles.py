"""Particle preset registry coherence with the native engine."""
from pathlib import Path
import re
import unittest

from dolly import particles

ROOT = Path(__file__).resolve().parents[1]


class ParticleRegistryTests(unittest.TestCase):
    def test_native_preset_table_matches_the_python_registry(self):
        header = (ROOT / "native/include/dolly_confetti.hpp").read_text(encoding="utf-8")
        count = int(re.search(r"kPresetCount\s*=\s*(\d+)", header).group(1))
        source = (ROOT / "native/src/dolly_confetti.cpp").read_text(encoding="utf-8")
        table = source[source.index("kPresets{{"):]
        ids = re.findall(r'\{"([a-z_]+)",', table)
        self.assertEqual(count, len(particles.PARTICLE_IDS))
        self.assertEqual(ids, list(particles.PARTICLE_IDS))

    def test_preset_index_and_labels_roundtrip(self):
        for index, name in enumerate(particles.PARTICLE_IDS):
            self.assertEqual(particles.preset_index(name), index)
            label = particles.PARTICLE_LABELS[name]
            self.assertEqual(particles.LABEL_TO_ID[label], name)
            self.assertEqual(particles.preset_label(name), label)
        with self.assertRaises(ValueError):
            particles.preset_index("missing")

    def test_intensity_defaults_are_encodable(self):
        from dolly import native_bridge as bridge

        raw = bridge._intensity_bits(particles.PARTICLE_INTENSITY_DEFAULT)
        self.assertEqual(raw, bridge.PARTICLE_INTENSITY_SCALE)
        self.assertLessEqual(raw, bridge.PARTICLE_INTENSITY_MASK)
        self.assertGreaterEqual(bridge._intensity_bits(particles.PARTICLE_INTENSITY_MIN), 2)


if __name__ == "__main__":
    unittest.main()
