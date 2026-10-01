"""Read-only verification of the stock spectator's exact player target."""
import struct
import hashlib

from .follow_capabilities import FollowCapabilityMonitor
from .preload import PreloadError
from .replay_camera import CLIENT_SHA256
from .preload import _image_bytes
from .replay_camera import ReplayCameraMonitor

TARGET_SPANS = ((0x15ee2f0, 0x79), (0x862f30, 5),
                (0x862f40, 0x5c), (0x8348f0, 0xc1))
# Exact stock HUD getter chain and its entity predicates. Camera mode alone
# cannot prove that health/ability children have a non-null player receiver.
HEALTH_CONTEXT_SPANS = ((0x92e2f0, 0x21), (0x15ee2d0, 0x17),
                        (0x576e30, 0xfc), (0x814960, 0x11),
                        (0x814980, 0x11), (0x862fd0, 0x89),
                        (0x1b12ef0, 0x129), (0x1b13540, 0x41),
                        (0x7bd600, 0x37), (0x4a0790, 5),
                        (0x710760, 3), (0x15cac20, 3),
                        (0x529c70, 3), (0x584f40, 3), (0x84cb70, 0x17c))


class FollowTargetMonitor(FollowCapabilityMonitor):
    """Uses the same exact-build/session gates as the rig capability sampler."""

    def __init__(self, session):
        # Include the separately reviewed observer getters in the code audit.
        from pathlib import Path
        from .preload import _image_bytes
        super().__init__(session)
        try:
            path = Path(self.command[0]).resolve().parents[2] / 'citadel/bin/win64/client.dll'
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != CLIENT_SHA256:
                raise PreloadError('Game Follow observer build is unsupported.')
            for rva, size in TARGET_SPANS:
                if self.memory.read(self.base + rva, size) != _image_bytes(data, rva, size):
                    raise PreloadError('Game Follow observer code differs from the reviewed build.')
        except BaseException:
            self.close()
            raise

    def sample_health_hud_context(self):
        """Allow only the reviewed spectator-to-selected-player HUD branch."""
        self._owned()
        if self.memory is None:
            raise PreloadError('Game Follow target monitor is closed.')
        for rva, size in HEALTH_CONTEXT_SPANS:
            if self.memory.read(self.base + rva, size) != _image_bytes(self._client_data, rva, size):
                raise PreloadError('Health HUD player getter code differs from the reviewed build.')
        before = ReplayCameraMonitor.sample(self)
        if not before.get('coherent') or not before.get('ready'):
            raise PreloadError('Health HUD requires a settled stock gameplay camera.')
        # The stock HUD getter rejects observer mode4; unlike Follow, it does
        # not require chase2/3. Still require a valid target/controller below.
        result = self.sample_target(require_chase=False, _require_health_context=True)
        after = ReplayCameraMonitor.sample(self)
        if not after.get('coherent') or not after.get('ready') or after != before:
            raise PreloadError('Health HUD stock camera changed during verification.')
        return result

    def sample_selection_context(self):
        """Prove the local observer can select; never authorize HUD reveal."""
        return self.sample_target(require_chase=False, _selection_only=True)

    def sample_target(self, *, require_chase=True, _require_health_context=False, _selection_only=False):
        self._owned()
        if self.memory is None:
            raise PreloadError('Game Follow target monitor is closed.')
        reads = []

        def read(address, size):
            value = self.memory.read(address, size)
            reads.append((address, value))
            return value

        def pointer(address):
            return struct.unpack('<Q', read(address, 8))[0]

        def uint(address):
            return struct.unpack('<I', read(address, 4))[0]

        def require_type(address, rvas):
            if not address or pointer(address) not in tuple(self.base + rva for rva in rvas):
                raise PreloadError('Game Follow observer object type differs from the reviewed build.')

        entity_system = pointer(self.base + 0x33e5d58)
        if not entity_system:
            raise PreloadError('Game Follow entity system is unavailable.')

        def resolve(handle):
            index = handle & 0x7fff
            if handle in (0xffffffff, 0xfffffffe) or index >= 0x7fff:
                raise PreloadError('Game Follow observer handle is unavailable.')
            chunk = pointer(entity_system + 8 * (index >> 9))
            if not chunk:
                raise PreloadError('Game Follow observer identity chunk is unavailable.')
            identity = chunk + 0x70 * (index & 0x1ff)
            if uint(identity + 0x10) != handle:
                raise PreloadError('Game Follow observer handle serial differs.')
            instance = pointer(identity)
            if not instance or pointer(instance + 0x10) != identity:
                raise PreloadError('Game Follow observer identity backpointer differs.')
            return instance

        controller = pointer(self.base + 0x3b7dba8)
        require_type(controller, (0x2686c08,))
        pawn = resolve(uint(controller + 0x6bc))
        require_type(pawn, (0x26041f8,))
        if _require_health_context:
            if (read(controller + 0x3ef, 1)[0] in (2, 3)
                    or read(pawn + 0x3ef, 1)[0] in (2, 3)
                    or pointer(self.base + 0x26041f8 + 0xac8) != self.base + 0x529c70):
                raise PreloadError('Health HUD requires the reviewed spectator player branch.')
        services = pointer(pawn + 0xe40)
        require_type(services, (0x2687650, 0x2a1c4e8))
        vtable = pointer(services)
        if (pointer(vtable + 0xf0) != self.base + 0x862f30
                or pointer(vtable + 0x100) != self.base + 0x862f40):
            raise PreloadError('Game Follow observer getters differ from the reviewed build.')
        mode = read(services + 0x48, 1)[0]
        if not _selection_only and (mode not in (0, 1, 2, 3) or (require_chase and mode not in (2, 3))):
            error = PreloadError(f'Game Follow requires a selected player chase view (observer mode {mode}).')
            error.observer_mode = mode
            raise error
        handle = uint(services + 0x4c)
        if _selection_only:
            pass  # Previous target may be absent/recycled; it will not be used.
        elif handle not in (0xffffffff, 0xfffffffe):
            target = resolve(handle)
            require_type(target, (0x2610c60,))
            if _require_health_context:
                if (pointer(self.base + 0x2610c60 + 0x4e0) != self.base + 0x15cac20
                        or pointer(self.base + 0x2610c60 + 0xac8) != self.base + 0x584f40):
                    raise PreloadError('Health HUD player predicates differ from the reviewed build.')
                target_controller = resolve(uint(target + 0x51c))
                require_type(target_controller, (0x2686c08,))
                if (pointer(self.base + 0x2686c08 + 0x4e8) != self.base + 0x710760
                        # Final network-bound type, not the temporary base
                        # vtable installed earlier inside the constructor.
                        or pointer(target_controller + 0x908) != self.base + 0x2686bd8):
                    raise PreloadError('Health HUD player data receiver differs from the reviewed build.')
        elif require_chase or _require_health_context:
            raise PreloadError('Game Follow observer target is unavailable.')
        if any(self.memory.read(address, len(value)) != value for address, value in reads):
            raise PreloadError('Game Follow observer target changed during verification.')
        self._owned()
        if _selection_only:
            return {'observer_mode': mode, 'previous_target_handle': handle}
        return {'handle': handle, 'entity_index': handle & 0x7fff, 'mode': mode}
