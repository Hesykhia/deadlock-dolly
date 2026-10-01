"""Read-only dashboard preload verification for Dolly-owned game processes.

This is independent of the camera backend. The layout is accepted only for the
reviewed client AND resource-system images; Native camera compatibility alone
does not authorize it. No game functions are called and no memory is written.
See docs/internal/PRELOAD.md for the reviewed predicate and update procedure.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import hashlib
import os
from pathlib import Path
import struct
import time


class PreloadError(RuntimeError):
    """Verification unavailable; never permission to dispatch a replay."""


class _ReviewedBuildMismatch(PreloadError):
    """A successful read disagreed with the reviewed build; never retried away."""


CLIENT_SHA256 = "cb244664a4b42057b02788bc95be489140fbba587266fdb40c5faf7d4d0784e3"
RESOURCE_SHA256 = "86d09bc988ab3609d43473c3fdc07246bd8958e7f8fc50af4bbba4ffe05a3da0"
MANAGER = 0x314b850
MANAGER_VTABLE = 0x2626058
RESOURCE_GLOBAL = 0x3d859b0
RESOURCE_VTABLE = 0x6bc58
RESOURCE_QUERY = 0x1c860
INTRO_GLOBAL = 0x3be53d8
INTRO_VTABLE = 0x2aae2b8

# Build 6731: status observes two lifecycle flags and consumes the finished
# job handle itself. Check the producer/callback as well as the UI predicate.
CLIENT_CODE_SPANS = (
    (0x5ed380, 8), (0x5f6620, 0x7e), (0x1cbd6e0, 0x10a),
    (0x5de5ae, 0x33), (0x5f99c0, 10), (0x5d24b0, 0x4b),
    (0x1a86e75, 0x65), (0x1aa4520, 0xe6),
    (0x1aca84e, 0x1d1), (0x1ab2f10, 0x42), (0x1a8fd50, 0x22a),
)


def _post_intro_escape(session):
    """Queue one Escape pair to the owned game window, never global input."""
    api = ctypes.WinDLL('user32', use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    api.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    api.EnumWindows.restype = wintypes.BOOL
    api.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    api.GetWindowThreadProcessId.restype = wintypes.DWORD
    api.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    api.GetWindowTextW.restype = ctypes.c_int
    api.IsWindowVisible.argtypes = [wintypes.HWND]
    api.IsWindowVisible.restype = wintypes.BOOL
    api.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    api.PostMessageW.restype = wintypes.BOOL
    candidates = []

    def owned(hwnd):
        owner = wintypes.DWORD()
        title = ctypes.create_unicode_buffer(256)
        api.GetWindowTextW(hwnd, title, len(title))
        return (session.running and api.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
                and owner.value == session.pid and title.value == 'Deadlock')

    @callback_type
    def visit(hwnd, _):
        if owned(hwnd) and api.IsWindowVisible(hwnd):
            candidates.append(hwnd)
        return True

    if not api.EnumWindows(visit, 0) or len(candidates) != 1:
        raise PreloadError('Cannot identify the owned Deadlock intro window.')
    hwnd = candidates[0]
    if not owned(hwnd):
        raise PreloadError('Deadlock intro window ownership changed.')
    # WM_KEYDOWN/UP, VK_ESCAPE, scan code 1. No focus change or SendInput.
    down = api.PostMessageW(hwnd, 0x100, 0x1b, 0x00010001)
    up = api.PostMessageW(hwnd, 0x101, 0x1b, 0xc0010001) if owned(hwnd) else False
    if not down or not up:
        raise PreloadError('Could not advance the Deadlock intro; replay remains unloaded.')


def _image_bytes(data, rva, size):
    """Read a reviewed PE's file-backed RVA without a runtime dependency."""
    try:
        pe = struct.unpack_from('<I', data, 0x3c)[0]
        if data[:2] != b'MZ' or data[pe:pe+4] != b'PE\0\0':
            raise ValueError('not PE')
        count = struct.unpack_from('<H', data, pe+6)[0]
        optional = struct.unpack_from('<H', data, pe+20)[0]
        for index in range(count):
            section = pe+24+optional+40*index
            start, raw_size, offset = struct.unpack_from('<III', data, section+12)
            if start <= rva and rva+size <= start+raw_size:
                result = data[offset+rva-start:offset+rva-start+size]
                if len(result) == size:
                    return result
    except (ValueError, struct.error):
        pass
    raise PreloadError('Could not verify the preload code image.')


class _Module(ctypes.Structure):
    _fields_ = [('size', wintypes.DWORD), ('module_id', wintypes.DWORD),
                ('pid', wintypes.DWORD), ('global_usage', wintypes.DWORD),
                ('process_usage', wintypes.DWORD), ('base', ctypes.c_void_p),
                ('image_size', wintypes.DWORD), ('module', wintypes.HMODULE),
                ('name', wintypes.WCHAR * 256), ('path', wintypes.WCHAR * 260)]


def _module_snapshot(api, pid):
    # Windows documents ERROR_BAD_LENGTH when the module list changes during
    # enumeration. Retry only that transient result, with a bounded wait.
    for attempt in range(8):
        snapshot = api.CreateToolhelp32Snapshot(0x8 | 0x10, pid)
        if snapshot != wintypes.HANDLE(-1).value:
            return snapshot
        error = ctypes.get_last_error()
        if error != 24 or attempt == 7:
            raise PreloadError(f'Cannot verify loaded preload modules (Windows error {error}).')
        time.sleep(.02)
    raise AssertionError('Unreachable snapshot retry state')


class _Memory:
    def __init__(self, session, executable):
        if os.name != 'nt' or ctypes.sizeof(ctypes.c_void_p) != 8:
            raise PreloadError('Preload verification requires 64-bit Windows.')
        self.handle = None
        self.bytes_read = 0
        self.api = api = ctypes.WinDLL('kernel32', use_last_error=True)
        api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        api.OpenProcess.restype = wintypes.HANDLE
        api.CloseHandle.argtypes = [wintypes.HANDLE]
        api.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                          ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
        api.ReadProcessMemory.restype = wintypes.BOOL
        api.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                                   wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
        api.QueryFullProcessImageNameW.restype = wintypes.BOOL
        api.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
        api.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
        for name in ('Module32FirstW', 'Module32NextW'):
            function = getattr(api, name)
            function.argtypes = [wintypes.HANDLE, ctypes.POINTER(_Module)]
            function.restype = wintypes.BOOL
        self.handle = api.OpenProcess(0x10 | 0x400, False, session.pid)
        if not self.handle:
            raise PreloadError('Cannot read preload status from the launched game.')
        try:
            path = ctypes.create_unicode_buffer(32768)
            size = wintypes.DWORD(len(path))
            if (not api.QueryFullProcessImageNameW(self.handle, 0, path, ctypes.byref(size))
                    or Path(path.value).resolve() != executable or not session.running):
                raise PreloadError('Preload process identity differs from the launched game.')
            self.modules = {}
            snapshot = _module_snapshot(api, session.pid)
            try:
                entry = _Module()
                entry.size = ctypes.sizeof(entry)
                valid = api.Module32FirstW(snapshot, ctypes.byref(entry))
                while valid:
                    self.modules[entry.name.casefold()] = (entry.base, Path(entry.path).resolve())
                    valid = api.Module32NextW(snapshot, ctypes.byref(entry))
            finally:
                api.CloseHandle(snapshot)
        except BaseException:
            self.close()
            raise

    def read(self, address, size):
        if not address or not 0x10000 <= address < 0x7fffffffffff or not 0 < size <= 4096:
            raise PreloadError('Invalid preload status address.')
        self.bytes_read += size
        if self.bytes_read > 4*1024*1024:
            raise PreloadError('Preload observation limit reached.')
        buffer, received = ctypes.create_string_buffer(size), ctypes.c_size_t()
        if (not self.api.ReadProcessMemory(self.handle, address, buffer, size, ctypes.byref(received))
                or received.value != size):
            raise PreloadError('Could not read complete preload status; replay remains unloaded.')
        return buffer.raw

    def pointer(self, address):
        return struct.unpack('<Q', self.read(address, 8))[0]

    def close(self):
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle = None


class PreloadMonitor:
    def __init__(self, session):
        self.session = session
        self.memory = None
        command = tuple(session.command)
        if (not session.running or not command or '-dev' not in command or '-insecure' not in command
                or tuple(session.process.args) != command or not session.owns_console_port()):
            raise PreloadError('Preload verification requires the Dolly-owned development session.')
        executable = Path(command[0]).resolve()
        game = executable.parents[2]
        paths = (game/'citadel/bin/win64/client.dll', game/'bin/win64/resourcesystem.dll')
        images = []
        for path, expected in zip(paths, (CLIENT_SHA256, RESOURCE_SHA256)):
            try:
                data = path.read_bytes()
            except OSError as exc:
                raise PreloadError('Cannot verify installed preload modules.') from exc
            observed = hashlib.sha256(data).hexdigest()
            if observed != expected:
                raise PreloadError(f'Preload verification is not supported for this game build '
                                   f'({path.name}: {observed}). Update Dolly or use manual startup; '
                                   'automatic replay loading was stopped.')
            images.append(data)
        try:
            self.memory = memory = _Memory(session, executable)
            bases = []
            for path in paths:
                module = memory.modules.get(path.name)
                if not module or module[1] != path.resolve():
                    raise PreloadError('Loaded preload module path differs from the reviewed installation.')
                bases.append(module[0])
            self.base, self.resource_base = bases
            for base, data, spans in (
                    (self.base, images[0], CLIENT_CODE_SPANS),
                    (self.resource_base, images[1], ((RESOURCE_QUERY, 13),))):
                for rva, length in spans:
                    if memory.read(base+rva, length) != _image_bytes(data, rva, length):
                        raise PreloadError('Live preload code differs from the reviewed game build.')
            self.identity = {'client_sha256': CLIENT_SHA256, 'resource_sha256': RESOURCE_SHA256,
                             'method': 'reviewed_dashboard_preload', 'pid': session.pid}
            self.intro_sent = False
        except BaseException:
            self.close()
            raise

    def sample(self):
        if not self.session.running:
            raise PreloadError('Deadlock closed during preload verification.')
        try:
            return self._sample()
        except _ReviewedBuildMismatch:
            raise
        except PreloadError:
            # The preload object lives in the game's writable data and can be
            # briefly unreadable while the hideout is still loading. That is
            # "not ready yet", not an incompatible build, so keep polling
            # rather than abort automatic startup. A read that succeeds but
            # contradicts the reviewed build still fails closed above.
            return {'coherent': False}

    def _sample(self):
        memory = self.memory
        raw = memory.read(self.base+MANAGER, 64)
        if raw != memory.read(self.base+MANAGER, 64):
            return {'coherent': False}
        if struct.unpack_from('<Q', raw)[0] != self.base+MANAGER_VTABLE:
            raise _ReviewedBuildMismatch('Preload object type differs from the reviewed build.')
        completed, total = struct.unpack_from('<ii', raw, 0x24)
        if not 0 <= completed <= 10000000 or not 0 <= total <= 10000000:
            raise _ReviewedBuildMismatch('Preload counters are outside their reviewed range.')
        resource = struct.unpack_from('<Q', raw, 0x30)[0]
        job = struct.unpack_from('<i', raw, 0x38)[0]
        scheduled, job_complete = raw[0x3c:0x3e]
        if scheduled not in (0, 1) or job_complete not in (0, 1):
            raise _ReviewedBuildMismatch('Preload lifecycle flags differ from the reviewed build.')
        # The resource-system global is populated partway through the hideout
        # load. Until then it reads as a null (or not-yet-mapped) pointer; that
        # is "not started", not a build mismatch, so it must not abort automatic
        # startup. A non-null value still has to match the reviewed vtable.
        system = memory.pointer(self.base+RESOURCE_GLOBAL)
        if not system:
            return {'coherent': False}
        try:
            vtable = memory.pointer(system)
        except PreloadError:
            return {'coherent': False}
        if (vtable != self.resource_base+RESOURCE_VTABLE
                or memory.pointer(vtable+0xc0) != self.resource_base+RESOURCE_QUERY):
            raise _ReviewedBuildMismatch('Resource completion query differs from the reviewed build.')
        resource_done = memory.read(resource+0x44, 1)[0] if resource else 1
        if resource_done not in (0, 1) or raw != memory.read(self.base+MANAGER, 64):
            return {'coherent': False}
        intro_phase = None
        if not resource:
            intro = memory.pointer(self.base+INTRO_GLOBAL)
            if intro:
                try:
                    state = memory.read(intro, 0x84)
                except PreloadError:
                    return {'coherent': False}
                if struct.unpack_from('<Q', state)[0] != self.base+INTRO_VTABLE:
                    raise _ReviewedBuildMismatch('Intro object type differs from the reviewed build.')
                intro_phase = struct.unpack_from('<i', state, 0x80)[0]
                if intro_phase not in (0, 1, 2, 3):
                    raise _ReviewedBuildMismatch('Unrecognized Deadlock intro state.')
                if (memory.pointer(self.base+INTRO_GLOBAL) != intro
                        or memory.read(intro+0x80, 4) != state[0x80:0x84]):
                    return {'coherent': False}
        return {'coherent': True, 'started': bool(resource), 'completed': completed, 'total': total,
                'intro_phase': intro_phase,
                'scheduled': bool(scheduled), 'job_complete': bool(job_complete),
                'resource_complete': bool(resource_done), 'job_active': job != 0,
                # Unlike the game's UI, never call an unscheduled preload ready.
                # Its status function waits/releases the completed job and clears
                # the handle; observe that final state without calling it ourselves.
                'ready': bool(resource) and scheduled == 1 and job_complete == 1
                         and job == 0 and resource_done == 1 and completed >= total}

    def advance_intro(self):
        """Only once, only at the reviewed interactive intro, with fresh state."""
        if self.intro_sent:
            return False
        sample = self.sample()
        if not sample.get('coherent') or sample.get('started') or sample.get('intro_phase') != 2:
            return False
        self.intro_sent = True
        _post_intro_escape(self.session)
        return True

    def close(self):
        if self.memory is not None:
            self.memory.close()
            self.memory = None
