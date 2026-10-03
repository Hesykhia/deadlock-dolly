"""Capability loss must stop the dependent feature before any game mutation."""
import unittest

from dolly import native_capabilities as caps, native_bridge as nb, editor_wire
from dolly.follow_camera import FollowSettings
import test_native_bridge as fixtures


def block(*, core=(1, 0), effects=(1, 0), follow=(1, 0), **fields):
    return caps.WIRE.pack(fields.get('magic', caps.MAGIC), fields.get('sequence', 2),
                          fields.get('abi', 1), fields.get('pid', 2002),
                          fields.get('count', 3), *core, *effects, *follow)


class CapabilityWireTests(unittest.TestCase):
    def test_follow_rejection_preserves_camera_and_all_required_gates(self):
        for follow in ((3, 2), (3, 3), (3, 4), (0, 0)):
            report = caps.unpack(block(follow=follow), 2002)
            self.assertTrue(caps.available(report, 'camera'))
            self.assertFalse(caps.available(report, 'follow'))
        for feature in ('core', 'effects'):
            for rejected in ((0, 0), (3, 1), (3, 2), (3, 3)):
                report = caps.unpack(block(**{feature: rejected}), 2002)
                self.assertFalse(caps.available(report, 'camera'))
                self.assertFalse(caps.available(report, 'follow'))

    def test_existing_reviewed_profiles_and_legacy_helpers_keep_their_behavior(self):
        self.assertIsNone(caps.unpack(bytes(caps.WIRE.size), 2002))
        self.assertTrue(caps.available(None, 'follow'))
        report = caps.unpack(block(effects=(2, 0), follow=(2, 0)), 2002)
        self.assertTrue(caps.available(report, 'camera'))
        self.assertTrue(caps.available(report, 'follow'))

    def test_invalid_or_foreign_blocks_never_authorize_a_feature(self):
        for fields in ({'magic': b'UNKNOWN!'}, {'abi': 2}, {'pid': 2003},
                       {'count': 2}, {'sequence': 3}, {'core': (2, 0)},
                       {'follow': (4, 0)}, {'follow': (3, 0)},
                       {'follow': (1, 2)}, {'follow': (3, 99)}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                caps.unpack(block(**fields), 2002)
        with self.assertRaises(ValueError):
            caps.unpack(block()[:-1], 2002)
        with self.assertRaises(ValueError):
            caps.available(None, 'misspelled')

    def test_wire_fits_between_existing_follow_and_camera_list_blocks(self):
        self.assertEqual(caps.OFFSET, nb.FOLLOW_ANCHOR_DIAGNOSTICS_OFFSET + nb.FOLLOW_ANCHOR_DIAGNOSTICS.size)
        self.assertLessEqual(caps.OFFSET + caps.WIRE.size, editor_wire.CAMERA_LIST_OFFSET)
        self.assertEqual(caps.WIRE.size, 48)


class CapabilityBridgeTests(unittest.TestCase):
    def setUp(self):
        self.memory = fixtures.Memory(nb.MAPPING_BYTES)
        self.bridge = nb.NativeBridge.create(mapping_factory=lambda *_: self.memory,
            editor_pid=1001, token='b' * 32, start_heartbeat=False)
        self.bridge.bind_game(2002)
        self.addCleanup(self.bridge.close)
        # Use the same real core-status fixture as the protocol regression suite.
        self.header = lambda: nb.CONTROL.unpack(self.memory[:nb.CONTROL.size])
        fixtures.NativeBridgeTests.publish_status(self)

    def publish(self, data):
        self.memory[caps.OFFSET:caps.OFFSET + len(data)] = data

    def test_failed_follow_keeps_camera_telemetry_and_disables_only_follow_controls(self):
        self.publish(block(follow=(3, 2)))
        self.assertTrue(self.bridge.capability_available('camera'))
        with self.assertRaisesRegex(nb.NativeBridgeError, 'Game Follow.*signature mismatch'):
            self.bridge.require_capability('follow')
        self.assertEqual(self.bridge.status()['applied_pose'], list(range(10, 17)))
        self.bridge.configure_editor_follow(FollowSettings(), available=True, active=True, pending=True)
        flags = editor_wire.FOLLOW_CONFIG.unpack_from(self.memory, editor_wire.FOLLOW_OFFSET)[3]
        self.assertEqual(flags, 6)  # Keep active/restore state; refuse a new preview.

    def test_corrupt_or_busy_capability_block_does_not_break_core_status(self):
        for data in (block(pid=999), block(sequence=3), block(abi=5)):
            self.publish(data)
            status = self.bridge.status()
            self.assertEqual(status['applied_pose'], list(range(10, 17)))
            self.assertIn('error', status['capabilities'])
            with self.assertRaises(nb.NativeBridgeError):
                self.bridge.require_capability('follow')

    def test_published_even_invalid_report_cannot_disappear_into_legacy_mode(self):
        for first in (block(), block(abi=9), block(sequence=3)):
            self.bridge._capabilities_seen = False
            self.publish(first)
            self.bridge.capabilities()
            self.publish(bytes(caps.WIRE.size))
            with self.assertRaisesRegex(nb.NativeBridgeError, 'disappeared'):
                self.bridge.require_capability('follow')

    def test_torn_read_is_retried_and_still_refuses_follow(self):
        self.publish(block())
        def changed(key):
            if isinstance(key, slice) and key.start == caps.OFFSET:
                self.memory.on_read = None
                self.publish(block(sequence=4, follow=(3, 3)))
        self.memory.on_read = changed
        self.assertFalse(self.bridge.capability_available('follow'))
        self.assertTrue(self.bridge.capability_available('camera'))

    def test_core_protocol_errors_still_refuse_camera_status(self):
        self.publish(block())
        fixtures.NativeBridgeTests.publish_status(self, pid=999)
        with self.assertRaisesRegex(nb.NativeBridgeError, 'different game process'):
            self.bridge.status()
