import unittest
from pathlib import Path
from unittest.mock import patch

from dolly import encoder_select
from dolly.video_export import VideoOptions, resolve_backend


class VendorDetectionTests(unittest.TestCase):
    def test_vendor_from_device_id_beats_description_keywords(self):
        self.assertEqual(encoder_select._vendor_from(r"PCI\VEN_10DE&DEV_2684", "Radeon"), "nvidia")
        self.assertEqual(encoder_select._vendor_from("", "AMD Radeon RX 7900 XTX"), "amd")
        self.assertEqual(encoder_select._vendor_from("", "ATI FirePro V"), "amd")
        self.assertEqual(encoder_select._vendor_from("", "Intel(R) UHD Graphics 770"), "intel")
        self.assertEqual(encoder_select._vendor_from("", "Microsoft Basic Render Driver"), "")

    def test_detect_vendor_uses_gpu_priority(self):
        self.assertEqual(encoder_select.detect_vendor((("intel", "UHD"), ("amd", "Radeon"))), "amd")
        self.assertEqual(encoder_select.detect_vendor((("amd", "Radeon"), ("nvidia", "RTX"))), "nvidia")
        self.assertEqual(encoder_select.detect_vendor((("intel", "UHD"),)), "intel")
        self.assertEqual(encoder_select.detect_vendor(()), "")

    def test_describe_adapters_names_every_detected_gpu(self):
        text = encoder_select.describe_adapters((("amd", "AMD Radeon RX 7900"), ("intel", "UHD")))
        self.assertIn("AMD Radeon RX 7900 [amd]", text)
        self.assertIn("UHD [intel]", text)
        self.assertEqual(encoder_select.describe_adapters(()), "no display adapters detected")


class AutoCodecTests(unittest.TestCase):
    def test_auto_maps_each_vendor_to_its_ffmpeg_encoder(self):
        for vendor, expected in (("nvidia", ("h264_nvenc", "NVIDIA H.264 (NVENC)")),
                                 ("amd", ("h264_amf", "AMD H.264 (AMF)")),
                                 ("intel", ("h264_qsv", "Intel H.264 (Quick Sync)"))):
            with self.subTest(vendor=vendor):
                self.assertEqual(encoder_select.auto_encoder(vendor), expected)

    def test_auto_uses_the_vendor_neutral_encoder_without_a_known_gpu(self):
        key, label = encoder_select.auto_encoder("")
        self.assertEqual(key, "h264_mf")
        self.assertIn("Media Foundation", label)

    def test_auto_consults_detection_when_no_vendor_is_given(self):
        with patch.object(encoder_select, "detect_vendor", return_value="amd"):
            self.assertEqual(encoder_select.auto_encoder()[0], "h264_amf")


class BackendResolutionTests(unittest.TestCase):
    def test_auto_maps_the_vendor_to_its_ffmpeg_encoder(self):
        options = VideoOptions(Path("out.mp4"), ffmpeg_path=Path("ffmpeg.exe"))
        for vendor, expected in (("nvidia", (1, 1)), ("amd", (1, 8)),
                                 ("intel", (1, 6)), ("", (1, 3)),
                                 ("unknown-vendor", (1, 3))):
            with self.subTest(vendor=vendor), \
                    patch.object(encoder_select, "detect_vendor", return_value=vendor):
                self.assertEqual(resolve_backend(options), expected)

    def test_auto_without_ffmpeg_keeps_the_built_in_encoder(self):
        self.assertEqual(resolve_backend(VideoOptions(Path("out.mp4"))), (0, 0))


if __name__ == "__main__":
    unittest.main()
