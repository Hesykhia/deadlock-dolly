"""Ordered restoration and detached cleanup failure boundaries."""
from pathlib import Path
import ctypes
import subprocess
import sys
from types import SimpleNamespace
import unittest
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

from dolly import launcher, graphics_profiles


def restore_trace(restore, *, pending=True, running=False, gameinfo_error=None,
                  graphics_error=None, pending_error=None, process_error=None):
    calls = []
    def gameinfo(session):
        calls.append('gameinfo')
        if gameinfo_error:
            raise gameinfo_error
        return True
    def graphics(session):
        calls.append('graphics')
        if graphics_error:
            raise graphics_error
    def is_pending(session):
        calls.append('pending')
        if pending_error:
            raise pending_error
        return pending
    def processes():
        calls.append('processes')
        if process_error:
            raise process_error
        return {'deadlock.exe'} if running else {'steam.exe'}
    error = None
    with patch.object(launcher, '_restore_record', side_effect=gameinfo), \
         patch.object(launcher, 'running_processes', side_effect=processes), \
         patch.object(graphics_profiles, 'restore', side_effect=graphics), \
         patch.object(graphics_profiles, 'pending', side_effect=is_pending):
        try:
            restore(Path('fixture'))
        except Exception as exc:
            error = {'type': type(exc).__name__, 'message': str(exc)}
    return {'calls': calls, 'error': error}


def waiter_trace(cleanup, scenario, *, lower_owners=True):
    from dolly import gameinfo_transaction, game_installation, game_processes, session_recovery
    calls = []
    load_count = 0
    remove_count = 0
    record = {'original_gameinfo': str(Path('fixture') / 'gameinfo.gi'),
              'overlay_dir': str(Path('fixture') / 'mount')}
    def load(session):
        nonlocal load_count
        load_count += 1
        calls.append('load')
        if scenario == 'bad_journal' or (scenario == 'second_load_failure' and load_count == 2):
            raise launcher.LaunchError('journal invalid')
        return record
    def restore(session):
        calls.append('restore')
        if scenario == 'restore_failure':
            raise launcher.LaunchError('restore conflict')
    def processes():
        calls.append('processes')
        return {'deadlock.exe'} if scenario == 'another_game' else {'steam.exe'}
    def validate(path):
        calls.append('validate')
        return SimpleNamespace()
    def remove(*args):
        nonlocal remove_count
        remove_count += 1
        calls.append('remove')
        if scenario == 'locked_forever' or (scenario == 'locked_twice' and remove_count < 3):
            raise OSError('DLL locked')
        if scenario == 'removal_refused':
            raise launcher.LaunchError('unknown contents')
        return scenario != 'already_removed'
    api = MagicMock()
    def wait(handle, timeout):
        calls.append(['wait', handle, timeout])
        return 0xFFFFFFFF if scenario == 'failed_wait' else 0
    api.WaitForSingleObject.side_effect = wait
    api.CloseHandle.side_effect = lambda handle: calls.append(['close_handle', handle])
    record_owner, record_name = (gameinfo_transaction, 'load_record') if lower_owners else (launcher, '_load_record')
    restore_owner, restore_name = (session_recovery, 'restore_session_configs') if lower_owners else (launcher, '_restore_session_configs')
    with ExitStack() as stack:
        for owner, name, function in ((record_owner, record_name, load), (restore_owner, restore_name, restore),
                (game_processes if lower_owners else launcher, 'running_processes', processes),
                (game_installation if lower_owners else launcher, 'validate_game', validate),
                (cleanup, 'remove_overlay', remove),
                (cleanup, '_append_log', lambda session, message: calls.append(['log', message])),
                (cleanup.time, 'sleep', lambda seconds: calls.append(['sleep', seconds]))):
            stack.enter_context(patch.object(owner, name, side_effect=function))
        stack.enter_context(patch.object(cleanup.sys, 'platform', 'win32'))
        stack.enter_context(patch.object(ctypes, 'WinDLL', return_value=api, create=True))
        result = cleanup.wait_and_cleanup(Path('fixture'), 5678)
    return {'result': result, 'calls': calls}


class SessionRecoveryTests(unittest.TestCase):
    def test_lower_recovery_imports_do_not_load_launcher_or_controller(self):
        result = subprocess.run([sys.executable, '-c',
            'import sys; import dolly.session_cleanup, dolly.session_recovery, dolly.graphics_profiles; '
            'assert not ({"dolly.launcher", "dolly.controller"} & sys.modules.keys())'],
            capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_waiter_keeps_six_attempts_and_five_half_second_delays(self):
        from dolly import session_cleanup
        trace = waiter_trace(session_cleanup, 'locked_forever')
        self.assertEqual(trace['result'], 1)
        self.assertEqual(trace['calls'].count('remove'), 6)
        self.assertEqual(trace['calls'].count(['sleep', .5]), 5)
        self.assertLess(trace['calls'].index(['close_handle', 5678]), trace['calls'].index('restore'))

    def test_waiter_failure_boundaries_never_remove_early(self):
        from dolly import session_cleanup
        for scenario in ('bad_journal', 'failed_wait', 'another_game', 'restore_failure', 'second_load_failure'):
            with self.subTest(scenario=scenario):
                trace = waiter_trace(session_cleanup, scenario)
                self.assertNotIn('remove', trace['calls'])
                self.assertEqual(trace['result'], 0 if scenario == 'another_game' else 1)
                if scenario != 'bad_journal':
                    self.assertIn(['close_handle', 5678], trace['calls'])

    def test_normal_and_nonpending_order(self):
        self.assertEqual(restore_trace(launcher._restore_session_configs),
                         {'calls': ['gameinfo', 'pending', 'processes', 'graphics'], 'error': None})
        self.assertEqual(restore_trace(launcher._restore_session_configs, pending=False),
                         {'calls': ['gameinfo', 'pending', 'graphics'], 'error': None})

    def test_both_errors_are_collected_in_restore_order(self):
        trace = restore_trace(launcher._restore_session_configs,
                              gameinfo_error=OSError('first conflict'),
                              graphics_error=launcher.LaunchError('second conflict'))
        self.assertEqual(trace['calls'], ['gameinfo', 'pending', 'processes', 'graphics'])
        self.assertEqual(trace['error'], {'type': 'LaunchError', 'message': 'first conflict\nsecond conflict'})

    def test_other_game_blocks_only_graphics_restoration(self):
        trace = restore_trace(launcher._restore_session_configs, running=True)
        self.assertEqual(trace['calls'], ['gameinfo', 'pending', 'processes'])
        self.assertEqual(trace['error'], {'type': 'LaunchError',
            'message': "Exit Deadlock before restoring this session's graphics settings."})

    def test_unreadable_pending_and_process_state_do_not_restore_graphics(self):
        for options, expected in (({'pending_error': launcher.LaunchError('journal unreadable')}, ['gameinfo','pending']),
                                  ({'process_error': OSError('enumeration failed')}, ['gameinfo','pending','processes'])):
            with self.subTest(options=options):
                trace = restore_trace(launcher._restore_session_configs, **options)
                self.assertEqual(trace['calls'], expected)
                self.assertEqual(trace['error']['type'], 'LaunchError')

    def test_unexpected_gameinfo_exception_stops_before_graphics(self):
        trace = restore_trace(launcher._restore_session_configs, gameinfo_error=RuntimeError('unexpected'))
        self.assertEqual(trace, {'calls': ['gameinfo'], 'error': {'type': 'RuntimeError', 'message': 'unexpected'}})

    def test_unexpected_graphics_exception_is_not_rewrapped(self):
        trace = restore_trace(launcher._restore_session_configs, graphics_error=ValueError('unexpected'))
        self.assertEqual(trace['calls'], ['gameinfo', 'pending', 'processes', 'graphics'])
        self.assertEqual(trace['error'], {'type': 'ValueError', 'message': 'unexpected'})


if __name__ == '__main__':
    unittest.main()
