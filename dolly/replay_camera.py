"""Read-only, exact-build verification of the replay's stock camera handoff.

GameInProgress alone does not end the scripted opening camera. Observe the
camera manager actually consumed by the main view, without skipping replay
packets, changing spectator mode, or invoking game functions.
"""
from pathlib import Path
import hashlib
import math
import struct

from .preload import _Memory, _image_bytes, PreloadError

from ._runtime_generated import ReplayCamera as _profile

CLIENT_SHA256 = _profile.CLIENT_SHA256
MANAGER = _profile.MANAGER
MANAGER_VTABLE = _profile.MANAGER_VTABLE
GAMEPLAY_CAMERA_VTABLE = _profile.GAMEPLAY_CAMERA_VTABLE
RULES_GLOBAL = _profile.RULES_GLOBAL
RULES_VTABLE = _profile.RULES_VTABLE
CODE_SPANS = _profile.CODE_SPANS


class ReplayCameraMonitor:
    def __init__(self, session):
        self.session = session
        self.memory = None
        self.command = tuple(session.command)
        self._owned()
        executable = Path(self.command[0]).resolve()
        path = executable.parents[2] / 'citadel/bin/win64/client.dll'
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != CLIENT_SHA256:
            raise PreloadError('Automatic replay camera handoff is unsupported for this game build. '
                               'Use manual startup or update Dolly.')
        try:
            self.memory = _Memory(session, executable)
            module = self.memory.modules.get('client.dll')
            if not module or module[1] != path.resolve():
                raise PreloadError('Replay camera module differs from the reviewed installation.')
            self.base = module[0]
            for rva, size in CODE_SPANS:
                if self.memory.read(self.base+rva, size) != _image_bytes(data, rva, size):
                    raise PreloadError('Replay camera code differs from the reviewed game build.')
            self.identity = {'client_sha256': CLIENT_SHA256, 'pid': session.pid,
                             'method': 'reviewed_stock_camera_handoff'}
        except BaseException:
            self.close()
            raise

    def _owned(self):
        if (not self.session.running or not self.command
                or '-dev' not in self.command or '-insecure' not in self.command
                or tuple(self.session.command) != self.command
                or tuple(self.session.process.args) != self.command
                or not self.session.owns_console_port()):
            raise PreloadError('Replay camera verification requires the owned development session.')

    def sample(self):
        self._owned()
        if self.memory is None:
            raise PreloadError('Replay camera monitor is closed.')
        m = self.memory
        unavailable = {'coherent': False, 'ready': False}
        try:
            rules = m.pointer(self.base+RULES_GLOBAL)
            if not rules:
                return unavailable
            rules_type = m.pointer(rules)
            raw_state = m.read(rules+_profile.RULES_STATE, 4)
            before = m.read(self.base+MANAGER, _profile.MANAGER_SIZE)
            current, previous = struct.unpack_from('<QQ', before, _profile.CURRENT_CAMERA)
            if not current:
                return unavailable
            current_type = m.pointer(current)
            previous_type = m.pointer(previous) if previous else None
            if (raw_state != m.read(rules+_profile.RULES_STATE, 4)
                    or m.pointer(self.base+RULES_GLOBAL) != rules
                    or m.pointer(rules) != rules_type
                    or m.read(self.base+MANAGER, _profile.MANAGER_SIZE) != before
                    or m.pointer(current) != current_type
                    or (previous and m.pointer(previous) != previous_type)):
                return unavailable
        except PreloadError:
            return unavailable
        if (rules_type != self.base+RULES_VTABLE
                or struct.unpack_from('<Q', before)[0] != self.base+MANAGER_VTABLE):
            raise PreloadError('Replay camera object type differs from the reviewed build.')
        state = struct.unpack('<i', raw_state)[0]
        blend = before[_profile.BLENDING]
        weight = struct.unpack_from('<f', before, _profile.BLEND_WEIGHT)[0]
        if (not 0 <= state <= 11 or blend not in (0, 1)
                or not math.isfinite(weight) or not 0 <= weight <= 1
                or (blend and not previous)):
            raise PreloadError('Replay camera state differs from the reviewed build.')
        return {'coherent': True, 'game_state': state, 'blending': bool(blend),
                'camera_vtable_rva': hex(current_type-self.base),
                'ready': state == 7 and not blend and current_type == self.base+GAMEPLAY_CAMERA_VTABLE}

    def close(self):
        if self.memory is not None:
            self.memory.close()
            self.memory = None
