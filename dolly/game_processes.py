"""Read-only process-name enumeration and Deadlock presence checks."""
from __future__ import annotations

import ctypes
import os

from .game_installation import GAME_EXECUTABLE_NAMES
from .launch_errors import LaunchError


def _game_is_running(processes: set[str]) -> bool:
    return any(name.casefold() in GAME_EXECUTABLE_NAMES for name in processes)


def running_processes() -> set[str]:
    """Enumerate process names without localized tasklist parsing or shell use."""
    if os.name != "nt":
        raise LaunchError("Deadlock Dolly's game launcher requires 64-bit Windows Python.")
    from ctypes import wintypes

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", wintypes.LONG),
            ("dwFlags", wintypes.DWORD), ("szExeFile", wintypes.WCHAR * 260),
        ]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    for name in ("Process32FirstW", "Process32NextW"):
        getattr(kernel, name).argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
        getattr(kernel, name).restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    snapshot = kernel.CreateToolhelp32Snapshot(2, 0)
    if snapshot == ctypes.c_void_p(-1).value:
        raise LaunchError("Could not inspect running processes; launch was refused.")
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(entry)
        if not kernel.Process32FirstW(snapshot, ctypes.byref(entry)):
            raise LaunchError("Could not inspect running processes; launch was refused.")
        names = set()
        while True:
            names.add(entry.szExeFile.casefold())
            if not kernel.Process32NextW(snapshot, ctypes.byref(entry)):
                if ctypes.get_last_error() not in (0, 18):  # ERROR_NO_MORE_FILES
                    raise LaunchError("Process enumeration was incomplete; launch was refused.")
                break
        return names
    finally:
        kernel.CloseHandle(snapshot)
