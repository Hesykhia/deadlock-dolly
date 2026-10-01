import struct
import unittest
from unittest.mock import Mock, patch

from dolly.follow_target import FollowTargetMonitor, HEALTH_CONTEXT_SPANS
from dolly.preload import PreloadError


class FollowTargetTests(unittest.TestCase):
    def health_fixture(self):
        m, blocks, chunk, services, target = self.fixture()
        m._client_data = b'fixture'
        for rva, size in HEALTH_CONTEXT_SPANS:
            blocks[m.base + rva] = b'\x90' * size
        def put(address, value, fmt='<Q'):
            blocks[address] = struct.pack(fmt, value)
        controller, pawn, hero_controller = 0x30000, 0x40000, 0x70000
        put(controller + 0x3ef, 1, '<B')
        put(pawn + 0x3ef, 1, '<B')
        for vtable, slot, getter in ((0x26041f8, 0xac8, 0x529c70),
                                    (0x2610c60, 0x4e0, 0x15cac20),
                                    (0x2610c60, 0xac8, 0x584f40),
                                    (0x2686c08, 0x4e8, 0x710760)):
            put(m.base + vtable + slot, m.base + getter)
        put(target + 0x51c, 0x18003, '<I')
        identity = chunk + 0x70 * 3
        put(identity, hero_controller)
        put(identity + 0x10, 0x18003, '<I')
        put(hero_controller + 0x10, identity)
        put(hero_controller, m.base + 0x2686c08)
        put(hero_controller + 0x908, m.base + 0x2686bd8)
        code = patch('dolly.follow_target._image_bytes', side_effect=lambda data, rva, size: b'\x90' * size)
        code.start()
        self.addCleanup(code.stop)
        camera = patch('dolly.follow_target.ReplayCameraMonitor.sample',
                       return_value={'coherent': True, 'ready': True})
        camera.start()
        self.addCleanup(camera.stop)
        return m, blocks, services, target, hero_controller

    def test_health_reveal_requires_typed_selected_controller_receiver(self):
        m, *_ = self.health_fixture()
        self.assertEqual(m.sample_health_hud_context()['handle'], 0x10002)

    def test_health_refuses_missing_recycled_or_wrong_player_data(self):
        for invalid in ('missing', 'recycled', 'receiver', 'base_constructor_type', 'controller_type', 'predicate'):
            with self.subTest(invalid=invalid):
                m, blocks, _, target, hero_controller = self.health_fixture()
                address, value, fmt = {
                    'missing': (target + 0x51c, 0xffffffff, '<I'),
                    'recycled': (target + 0x51c, 0x20003, '<I'),
                    'receiver': (hero_controller + 0x908, 0, '<Q'),
                    'base_constructor_type': (hero_controller + 0x908, m.base + 0x267c5f8, '<Q'),
                    'controller_type': (hero_controller, m.base + 0x26041f8, '<Q'),
                    'predicate': (m.base + 0x2686c08 + 0x4e8, m.base + 0x584f40, '<Q'),
                }[invalid]
                blocks[address] = struct.pack(fmt, value)
                with self.assertRaises(PreloadError):
                    m.sample_health_hud_context()

    def test_health_refuses_unreviewed_mode_and_playing_team_fallbacks(self):
        for address, value in ((0x30000 + 0x3ef, 2), (0x40000 + 0x3ef, 3),
                               (0x50000 + 0x48, 4)):
            m, blocks, *_ = self.health_fixture()
            blocks[address] = bytes([value])
            with self.assertRaises(PreloadError):
                m.sample_health_hud_context()

    def test_health_original_modes_need_valid_player_not_follow_chase(self):
        for mode in (0, 1, 2, 3):
            with self.subTest(mode=mode):
                m, blocks, services, *_ = self.health_fixture()
                blocks[services + 0x48] = bytes([mode])
                self.assertEqual(m.sample_health_hud_context()['mode'], mode)
                blocks[services + 0x4c] = struct.pack('<I', 0xffffffff)
                with self.assertRaises(PreloadError):
                    m.sample_health_hud_context()

    def test_selection_can_leave_unreviewed_mode_without_authorizing_reveal(self):
        m, blocks, _, services, _ = self.fixture()
        blocks[services + 0x48] = bytes([4])
        blocks[services + 0x4c] = struct.pack('<I', 0xffffffff)
        self.assertEqual(m.sample_selection_context(), {'observer_mode': 4, 'previous_target_handle': 0xffffffff})
        with self.assertRaises(PreloadError) as error:
            m.sample_target(require_chase=False)
        self.assertEqual(error.exception.observer_mode, 4)

    def test_selection_still_requires_local_observer_identity(self):
        m, blocks, *_ = self.fixture()
        blocks[0x40000] = struct.pack('<Q', m.base + 0x2610c60)
        with self.assertRaises(PreloadError):
            m.sample_selection_context()

    def test_health_refuses_torn_receiver(self):
        m, blocks, _, _, hero_controller = self.health_fixture()
        address = hero_controller + 0x908
        read = m.memory.read.side_effect
        count = 0
        def changing_read(where, size):
            nonlocal count
            if where == address:
                count += 1
                if count > 1:
                    return struct.pack('<Q', 0)
            return read(where, size)
        m.memory.read.side_effect = changing_read
        with self.assertRaisesRegex(PreloadError, 'changed during'):
            m.sample_health_hud_context()

    def test_health_refuses_changed_code_or_unsettled_camera(self):
        m, blocks, *_ = self.health_fixture()
        rva, size = HEALTH_CONTEXT_SPANS[0]
        blocks[m.base + rva] = b'\x00' * size
        with self.assertRaisesRegex(PreloadError, 'code differs'):
            m.sample_health_hud_context()
        blocks[m.base + rva] = b'\x90' * size
        with patch('dolly.follow_target.ReplayCameraMonitor.sample', side_effect=[
                {'coherent': True, 'ready': True}, {'coherent': True, 'ready': False}]):
            with self.assertRaisesRegex(PreloadError, 'camera changed'):
                m.sample_health_hud_context()

    def fixture(self):
        m = FollowTargetMonitor.__new__(FollowTargetMonitor)
        m.base = 0x180000000
        m._owned = Mock()
        blocks = {}
        def put(address, value, fmt='<Q'):
            blocks[address] = struct.pack(fmt, value)
        system, chunk, controller, pawn, services, target = range(0x10000, 0x70000, 0x10000)
        put(m.base + 0x33e5d58, system)
        put(system, chunk)
        put(m.base + 0x3b7dba8, controller)
        put(controller, m.base + 0x2686c08)
        put(controller + 0x6bc, 0x8001, '<I')
        for handle, instance, vt in ((0x8001, pawn, 0x26041f8), (0x10002, target, 0x2610c60)):
            identity = chunk + 0x70 * (handle & 0x1ff)
            put(identity, instance)
            put(identity + 0x10, handle, '<I')
            put(instance + 0x10, identity)
            put(instance, m.base + vt)
        put(pawn + 0xe40, services)
        put(services, m.base + 0x2687650)
        put(m.base + 0x2687650 + 0xf0, m.base + 0x862f30)
        put(m.base + 0x2687650 + 0x100, m.base + 0x862f40)
        put(services + 0x48, 2, '<B')
        put(services + 0x4c, 0x10002, '<I')
        m.memory = Mock()
        m.memory.read.side_effect = lambda address, size: blocks[address][:size]
        return m, blocks, chunk, services, target

    def test_exact_full_handle(self):
        m, *_ = self.fixture()
        self.assertEqual(m.sample_target(), {'handle': 0x10002, 'entity_index': 2, 'mode': 2})
        self.assertEqual(m._owned.call_count, 2)

    def test_hotfix_base_observer_type_and_getters(self):
        m, blocks, _, services, _ = self.fixture()
        table = m.base + 0x2a1c4e8
        blocks[services] = struct.pack('<Q', table)
        blocks[table + 0xf0] = struct.pack('<Q', m.base + 0x862f30)
        blocks[table + 0x100] = struct.pack('<Q', m.base + 0x862f40)
        self.assertEqual(m.sample_target()['handle'], 0x10002)
        # The prior build's nearby table must never satisfy this exact type gate.
        blocks[services] = struct.pack('<Q', m.base + 0x2a191c8)
        with self.assertRaisesRegex(PreloadError, 'object type differs'):
            m.sample_target()

    def test_prior_build_observer_getter_refused(self):
        m, blocks, *_ = self.fixture()
        blocks[m.base + 0x2687650 + 0xf0] = struct.pack('<Q', m.base + 0x860a40)
        with self.assertRaisesRegex(PreloadError, 'getters differ'):
            m.sample_target()

    def test_recycled_handle_and_backpointer_refused(self):
        for backpointer in (False, True):
            m, blocks, chunk, _, target = self.fixture()
            address = target + 0x10 if backpointer else chunk + 0xe0 + 0x10
            blocks[address] = struct.pack('<Q' if backpointer else '<I', 2)
            with self.assertRaises(PreloadError):
                m.sample_target()

    def test_wrong_type_or_mode_refused(self):
        for wrong_mode in (False, True):
            m, blocks, _, services, target = self.fixture()
            blocks[services + 0x48 if wrong_mode else target] = (
                b'\x01' if wrong_mode else struct.pack('<Q', m.base + 0x26041f8))
            with self.assertRaises(PreloadError):
                m.sample_target()

    def test_torn_target_refused(self):
        m, blocks, _, services, _ = self.fixture()
        seen = set()
        def read(address, size):
            value = blocks[address][:size]
            if address == services + 0x4c and address in seen:
                return struct.pack('<I', 0x18002)
            seen.add(address)
            return value
        m.memory.read.side_effect = read
        with self.assertRaisesRegex(PreloadError, 'changed during'):
            m.sample_target()

    def test_unowned_does_not_read(self):
        m, *_ = self.fixture()
        m._owned.side_effect = PreloadError('unowned')
        with self.assertRaises(PreloadError):
            m.sample_target()
        m.memory.read.assert_not_called()
