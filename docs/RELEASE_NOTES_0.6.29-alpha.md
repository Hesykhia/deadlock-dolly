# Deadlock Dolly 0.6.29-alpha

A reliability fix for the automatic updater.

## Highlights

- **Automatic updates are more reliable.** *Before:* on some installs the update failed with "[WinError 5] Access is denied" while replacing a file, so the update never finished (your previous files were kept). *After:* Dolly clears a read-only attribute left by ZIP extraction, retries the file move briefly, and if Windows still blocks it, explains what to do (move Dolly out of a protected folder such as Downloads, or allow it in Controlled Folder Access) instead of just failing.

## Changes

- `dolly/update_worker.py`: `replace_file` clears the read-only attribute on the target and retries `os.replace` on WinError 5/32 before failing closed; the failure dialog adds guidance for a locked or protected folder.
- Tests cover a transient lock (retried), a persistent lock (fails closed and rolls back) and a read-only target.

## Validation

Offline: 1,891 Python tests pass with 15 skipped; the native build and packaged portable-editor self-test pass.

## Updating

If you are on an older build whose updater is failing, download the Windows ZIP once and extract it to a folder outside a protected location (for example not Downloads), then run Dolly.exe. Later updates install automatically. Python and Tcl/Tk are bundled.
