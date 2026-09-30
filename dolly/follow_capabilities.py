"""Exact-build, read-only type/flag checks for the stock follow-camera rig."""
from pathlib import Path
import hashlib
import struct

from .follow_camera import ENABLED, FOLLOW_AIM, PREFIX, validate_value
from .preload import PreloadError, _image_bytes
from .replay_camera import CLIENT_SHA256, ReplayCameraMonitor

TIER0_SHA256 = '493bf3ca610bac0eec1369d19aa67f4c279c6ae1c8f1243b3bad0974c6a8db82'
CLIENT_SPANS = ((0x8ecb0, 0xd66), (0x90700, 0xa6), (0x230670, 0x73),
                (0x23a1680, 0x81), (0x24dd60, 0xa), (0x604cb6, 0xb))
TIER0_SPANS = ((0x20fd40, 0x279),)
REFS = {
    'pivot_x_offset': 0x35f7190, 'pivot_y_offset': 0x35f71a0,
    'pivot_z_offset': 0x35f71b0, 'pivot_x_offset_crouching': 0x35f71c0,
    'pivot_y_offset_crouching': 0x35f71d0, 'pivot_z_offset_crouching': 0x35f71e0,
    'x_offset': 0x35f71f0, 'y_offset': 0x35f7200, 'z_offset': 0x35f7210,
    'x_worst_case_offset': 0x35f7220, 'y_worst_case_offset': 0x35f7230,
    'z_worst_case_offset': 0x35f7240, 'ads_x_offset': 0x35f7250,
    'ads_y_offset': 0x35f7260, 'ads_z_offset': 0x35f7270,
    'fov': 0x35f7280, 'ads_fov': 0x35f7290,
}
# Same blocked bits as the existing reviewed native effect binding.
BLOCKED_FLAGS = sum(1 << bit for bit in (2, 9, 10, 13, 15, 18, 22))
OWN_HEALTH_HUD = 'citadel_hud_hide_own_health'
OWN_HEALTH_SPANS = ((0x1b6b90, 0xae), (0x1acaee0, 0x347), (0x1aac7e0, 0x2f))
# Current settings-checkbox binding marks its own ConVar with bit30. This
# allowance belongs only to this reviewed panel, never the shared rig policy.
OWN_HEALTH_ALLOWED_FLAGS = 0x40080088


class FollowCapabilityMonitor(ReplayCameraMonitor):
    def __init__(self, session):
        super().__init__(session)
        try:
            executable = Path(self.command[0]).resolve()
            client_path = executable.parents[2] / 'citadel/bin/win64/client.dll'
            tier0_path = executable.parent / 'tier0.dll'
            client_data = client_path.read_bytes()
            tier0_data = tier0_path.read_bytes()
            if hashlib.sha256(client_data).hexdigest() != CLIENT_SHA256:
                raise PreloadError('Game Follow client build is unsupported.')
            if hashlib.sha256(tier0_data).hexdigest() != TIER0_SHA256:
                raise PreloadError('Game Follow tier0 build is unsupported.')
            module = self.memory.modules.get('tier0.dll')
            if not module or module[1] != tier0_path.resolve():
                raise PreloadError('Game Follow tier0 module path differs from the reviewed installation.')
            for base, data, spans, image_size in (
                    (self.base, client_data, CLIENT_SPANS, 0x40f5000),
                    (module[0], tier0_data, TIER0_SPANS, 0x401000)):
                pe_offset = struct.unpack_from('<I', data, 0x3c)[0]
                size_address = pe_offset + 24 + 56
                if (struct.unpack_from('<I', data, size_address)[0] != image_size
                        or self.memory.read(base + size_address, 4) != struct.pack('<I', image_size)):
                    raise PreloadError('Game Follow module image size differs from the reviewed build.')
                for rva, size in spans:
                    if self.memory.read(base + rva, size) != _image_bytes(data, rva, size):
                        raise PreloadError('Game Follow code differs from the reviewed build.')
            self.identity.update(tier0_sha256=TIER0_SHA256,
                                 method='reviewed_stock_follow_cvar_refs')
            self._client_data = client_data
        except BaseException:
            self.close()
            raise

    def sample(self):
        self._owned()
        if self.memory is None:
            raise PreloadError('Game Follow capability monitor is closed.')
        refs = {PREFIX + suffix: (rva, 7) for suffix, rva in REFS.items()}
        refs.update({ENABLED: (0x35f7180, 0), FOLLOW_AIM: (0x35f6eb0, 0)})
        result = {}
        for name, (rva, expected_type) in refs.items():
            result[name] = self._sample_ref(name, rva, expected_type, 0x80080,
                                           lambda value: validate_value(name, value))
        self._owned()
        return result

    def sample_own_health(self):
        """Separate stock HUD panel; never disables health renderers."""
        self._owned()
        if self.memory is None:
            raise PreloadError('Game Follow capability monitor is closed.')
        for rva, size in OWN_HEALTH_SPANS:
            if self.memory.read(self.base + rva, size) != _image_bytes(self._client_data, rva, size):
                raise PreloadError('Health HUD panel code differs from the reviewed build.')
        def boolean(value):
            if value not in (0, 1):
                raise ValueError('Health HUD panel setting must be boolean.')
            return float(value)
        result = self._sample_ref(OWN_HEALTH_HUD, 0x3bdf698, 0, 0x80000, boolean,
                                  allowed_flags=OWN_HEALTH_ALLOWED_FLAGS)
        self._owned()
        return result

    def _sample_ref(self, name, rva, expected_type, required_flags, validator,
                    allowed_flags=None):
        ref = self.memory.read(self.base + rva, 16)
        identifier, data = struct.unpack('<QQ', ref)
        if not data or identifier & 0xffff == 0xffff:
            raise PreloadError('Game Follow setting is not registered: ' + name)
        header = self.memory.read(data, 0x5c)
        name_pointer = struct.unpack_from('<Q', header)[0]
        expected_name = name.encode('ascii') + b'\0'
        actual_name = self.memory.read(name_pointer, len(expected_name))
        if (self.memory.read(self.base + rva, 16) != ref
                or self.memory.read(data, 0x5c) != header
                or self.memory.read(name_pointer, len(expected_name)) != actual_name):
            raise PreloadError('Game Follow setting changed during verification: ' + name)
        value_type = struct.unpack_from('<H', header, 0x28)[0]
        flags = struct.unpack_from('<Q', header, 0x30)[0]
        if actual_name != expected_name or value_type != expected_type:
            raise PreloadError('Game Follow setting identity/type differs: ' + name)
        value = header[0x58] if value_type == 0 else struct.unpack_from('<f', header, 0x58)[0]
        try:
            value = validator(value)
        except ValueError as exc:
            raise PreloadError('Game Follow setting value is invalid: ' + name) from exc
        capability = {'value': value, 'type': value_type, 'flags': flags, 'ref_rva': hex(rva)}
        if (flags & BLOCKED_FLAGS or flags & required_flags != required_flags
                or (allowed_flags is not None and flags & ~allowed_flags)):
            error = PreloadError('Game Follow setting has unsupported runtime flags: ' + name + f' ({flags:#x})')
            error.capability = capability  # Read-only refusal evidence; never authorizes a setter.
            raise error
        return capability
