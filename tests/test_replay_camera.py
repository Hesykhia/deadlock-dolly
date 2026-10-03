"""A running match must not bypass the scripted camera or an unfinished blend."""
import struct
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from dolly import replay_camera as camera
from dolly.preload import PreloadError


class ReplayCameraTests(unittest.TestCase):
    def test_unowned_launch_is_rejected_before_opening_process(self):
        command = ('deadlock.exe', '-dev')
        session = SimpleNamespace(command=command, running=True,
                                  process=SimpleNamespace(args=command), owns_console_port=lambda: True)
        with patch.object(camera, '_Memory') as memory:
            with self.assertRaisesRegex(PreloadError, 'owned development'):
                camera.ReplayCameraMonitor(session)
        memory.assert_not_called()

    def test_unknown_client_hash_never_opens_process(self):
        with tempfile.TemporaryDirectory() as directory:
            game = Path(directory)/'game'
            executable = game/'bin/win64/deadlock.exe'
            client = game/'citadel/bin/win64/client.dll'
            client.parent.mkdir(parents=True)
            client.write_bytes(b'unknown client')
            command = (str(executable), '-dev', '-insecure')
            session = SimpleNamespace(command=command, running=True,
                                      process=SimpleNamespace(args=command), owns_console_port=lambda: True)
            with patch.object(camera, '_Memory') as memory:
                with self.assertRaisesRegex(PreloadError, 'unsupported'):
                    camera.ReplayCameraMonitor(session)
            memory.assert_not_called()

    def monitor(self, *, state=7, blend=0, weight=0., current_type=None, previous=0):
        m = camera.ReplayCameraMonitor.__new__(camera.ReplayCameraMonitor)
        m.base = 0x180000000
        m._owned = lambda: None
        raw = bytearray(0x48)
        struct.pack_into('<Q', raw, 0, m.base+camera.MANAGER_VTABLE)
        struct.pack_into('<QQ', raw, 0x28, 0x200000, previous)
        raw[0x38] = blend
        struct.pack_into('<f', raw, 0x44, weight)
        blocks = {m.base+camera.MANAGER: raw, 0x100074: struct.pack('<i', state)}
        pointers = {m.base+camera.RULES_GLOBAL: 0x100000,
                    0x100000: m.base+camera.RULES_VTABLE,
                    0x200000: m.base+(current_type or camera.GAMEPLAY_CAMERA_VTABLE),
                    0x300000: m.base+0x2a42458}
        m.memory = Mock()
        m.memory.read.side_effect = lambda address, size: bytes(blocks[address])[:size]
        m.memory.pointer.side_effect = pointers.__getitem__
        return m, blocks, pointers

    def test_normal_camera_is_ready_only_in_gameplay(self):
        for state in (0, 4, 5, 6, 7, 8):
            m, _, _ = self.monitor(state=state)
            self.assertEqual(m.sample()['ready'], state == 7)

    def test_scripted_unknown_and_blending_cameras_wait(self):
        for kwargs in ({'current_type': 0x2a42458}, {'current_type': 0x123456},
                       {'blend': 1, 'weight': .99, 'previous': 0x300000}):
            m, _, _ = self.monitor(**kwargs)
            self.assertFalse(m.sample()['ready'])

    def test_invalid_successful_reads_fail_closed(self):
        for kwargs in ({'blend': 2}, {'blend': 1}, {'weight': float('nan')},
                       {'weight': float('inf')}, {'weight': 1.5}, {'state': 100}):
            m, _, _ = self.monitor(**kwargs)
            with self.assertRaises(PreloadError):
                m.sample()

    def test_type_mismatch_is_not_retried_into_readiness(self):
        m, _, pointers = self.monitor()
        pointers[0x100000] += 8
        with self.assertRaisesRegex(PreloadError, 'object type'):
            m.sample()

    def test_unreadable_or_missing_rules_never_report_ready(self):
        m, _, pointers = self.monitor()
        pointers[m.base+camera.RULES_GLOBAL] = 0
        self.assertFalse(m.sample()['ready'])
        m.memory.pointer.side_effect = PreloadError('unmapped')
        self.assertFalse(m.sample()['ready'])

    def test_camera_switch_during_read_is_not_a_coherent_snapshot(self):
        m, blocks, _ = self.monitor()
        reads = 0
        def read(address, size):
            nonlocal reads
            data = bytes(blocks[address])
            if address == m.base+camera.MANAGER:
                reads += 1
                if reads == 2:
                    changed = bytearray(data)
                    struct.pack_into('<Q', changed, 0x28, 0x300000)
                    return bytes(changed)
            return data[:size]
        m.memory.read.side_effect = read
        self.assertFalse(m.sample()['coherent'])

    def startup_monitor(self, count=0):
        m, blocks, pointers = self.monitor()
        pointers[m.base+0x3c33c18] = 0x400000
        pointers[0x400000] = m.base+0x2adea98
        blocks[0x400284] = struct.pack('<i', count)
        return m, blocks, pointers

    def test_startup_waits_for_cinematic_hud_after_camera_is_ready(self):
        m, blocks, _ = self.startup_monitor(count=1)
        self.assertTrue(m.sample()['ready'])  # Health/Follow camera contract unchanged.
        before = m.sample_startup()
        self.assertTrue(before['camera_ready'])
        self.assertFalse(before['ready'])
        self.assertEqual(before['hud_takeover_count'], 1)
        blocks[0x400284] = struct.pack('<i', 0)
        self.assertTrue(m.sample_startup()['ready'])

    def test_missing_hud_does_not_admit_startup(self):
        m, _, pointers = self.startup_monitor()
        pointers[m.base+0x3c33c18] = 0
        self.assertFalse(m.sample_startup()['ready'])

    def test_wrong_hud_type_and_invalid_counter_fail_closed(self):
        m, _, pointers = self.startup_monitor()
        pointers[0x400000] += 8
        with self.assertRaisesRegex(PreloadError, 'HUD object type'):
            m.sample_startup()
        for count in (-1, 17):
            m, _, _ = self.startup_monitor(count)
            with self.assertRaisesRegex(PreloadError, 'takeover count'):
                m.sample_startup()

    def test_hud_transition_during_read_is_not_ready(self):
        m, blocks, _ = self.startup_monitor(count=1)
        reads = 0
        def read(address, size):
            nonlocal reads
            if address == 0x400284:
                reads += 1
                if reads == 2:
                    return struct.pack('<i', 0)
            return bytes(blocks[address])[:size]
        m.memory.read.side_effect = read
        self.assertFalse(m.sample_startup()['ready'])

    def test_unreadable_hud_never_admits_startup(self):
        m, _, pointers = self.startup_monitor()
        def pointer(address):
            if address == m.base+0x3c33c18:
                raise PreloadError('unmapped HUD')
            return pointers[address]
        m.memory.pointer.side_effect = pointer
        self.assertFalse(m.sample_startup()['ready'])

    def test_camera_change_across_hud_read_invalidates_startup_sample(self):
        m, _, _ = self.startup_monitor()
        with patch.object(m, 'sample', side_effect=[{'coherent': True, 'ready': True},
                                                   {'coherent': True, 'ready': False}]):
            self.assertFalse(m.sample_startup()['coherent'])
