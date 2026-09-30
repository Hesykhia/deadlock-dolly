import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from types import SimpleNamespace

from dolly import editor_session
from dolly.follow_camera import BOUNDS, PREFIX, ENABLED, FollowSettings
from tests.test_native_flight_controller import configured_controller


class FollowControllerTests(unittest.TestCase):
    def select_fixture(self):
        player = {'handle': 0x10002, 'entity_index': 2, 'model': 0x123456789abcdef,
                  'model_path': 'models/heroes/frank/frank.vmdl'}
        self.bridge.editor_roster = Mock(return_value={'players': [player]})
        target = Mock()
        target.sample_target.return_value = {'handle': player['handle'], 'mode': 2}
        return player, target

    def test_stock_selection_verifies_target_then_applies(self):
        player, target = self.select_fixture()
        with patch('dolly.follow_target.FollowTargetMonitor', return_value=target):
            self.c.start_selected_game_follow(FollowSettings(), player)
        self.assertTrue(self.c._follow_active)
        self.assertIn('spec_target 2', self.console.events)
        target.close.assert_called_once()

    def test_stale_player_refused_before_command_or_monitor(self):
        player, _ = self.select_fixture()
        self.bridge.editor_roster.return_value = {'players': []}
        with patch('dolly.follow_target.FollowTargetMonitor') as factory:
            with self.assertRaisesRegex(RuntimeError, 'current roster'):
                self.c.start_selected_game_follow(FollowSettings(), player)
        factory.assert_not_called()
        self.assertEqual(self.console.values, self.originals)

    def test_directed_mode_explicitly_changes_to_chase_and_restores(self):
        player, target = self.select_fixture()
        self.console.values['citadel_spectator_mode'] = 0.
        with patch('dolly.follow_target.FollowTargetMonitor', return_value=target):
            self.c.start_selected_game_follow(FollowSettings(), player)
        self.assertEqual(self.console.values['citadel_spectator_mode'], 2.)
        self.assertEqual(self.c._follow_mode_original, 0.)
        self.c.stop_game_follow()
        self.assertEqual(self.console.values['citadel_spectator_mode'], 0.)
        self.assertIsNone(self.c._follow_mode_original)

    def test_failed_confirmation_restores_original_mode(self):
        player, target = self.select_fixture()
        self.console.values['citadel_spectator_mode'] = 0.
        target.sample_target.side_effect = [
            {'handle': player['handle'], 'mode': 2}, RuntimeError('target unavailable')]
        with patch('dolly.follow_target.FollowTargetMonitor', return_value=target):
            with self.assertRaisesRegex(RuntimeError, 'target unavailable'):
                self.c.start_selected_game_follow(FollowSettings(), player)
        self.assertEqual(self.console.values['citadel_spectator_mode'], 0.)
        self.assertFalse(self.c._follow_active)
        self.assertEqual(self.console.values[ENABLED], self.originals[ENABLED])

    def test_mode_restore_cannot_touch_different_session(self):
        player, target = self.select_fixture()
        self.console.values['citadel_spectator_mode'] = 0.
        with patch('dolly.follow_target.FollowTargetMonitor', return_value=target):
            self.c.start_selected_game_follow(FollowSettings(), player)
        self.c._follow_transaction = None
        self.c._session = object()
        with self.assertRaisesRegex(RuntimeError, 'different session'):
            self.c.stop_game_follow()
        self.assertEqual(self.c._follow_mode_original, 0.)
        self.assertEqual(self.console.values['citadel_spectator_mode'], 2.)

    def test_nonobserver_refused_before_camera_handoff(self):
        player, target = self.select_fixture()
        target.sample_selection_context.side_effect = RuntimeError('wrong observer type')
        with patch('dolly.follow_target.FollowTargetMonitor', return_value=target), patch.object(self.c, 'toggle_game_ui') as handoff:
            with self.assertRaisesRegex(RuntimeError, 'observer type'):
                self.c.start_selected_game_follow(FollowSettings(), player)
        handoff.assert_not_called()
        self.assertEqual(self.console.values, self.originals)
        target.close.assert_called_once()

    def test_changed_target_after_apply_restores_rig(self):
        player, target = self.select_fixture()
        target.sample_target.side_effect = [
            {'handle': player['handle'], 'mode': 2},
            {'handle': 0x18002, 'mode': 2}]
        with patch('dolly.follow_target.FollowTargetMonitor', return_value=target):
            with self.assertRaisesRegex(RuntimeError, 'hero changed'):
                self.c.start_selected_game_follow(FollowSettings(), player)
        self.assertFalse(self.c._follow_active)
        self.assertEqual(self.console.values[ENABLED], self.originals[ENABLED])

    def setUp(self):
        self.c, self.console, self.bridge = configured_controller()
        self.console.values.update({PREFIX + name: float((low + high) / 2)
                                    for name, (low, high) in BOUNDS.items()})
        self.console.values.update({ENABLED: 0., 'citadel_camera_spectator_auto_target_view': 0.,
                                    'citadel_spectator_mode': 2.})
        self.c._game_ui_visible = True
        self.c._recorder_active = Mock(return_value=False)
        self.originals = dict(self.console.values)
        self.monitor = Mock()
        self.monitor.sample.side_effect = lambda: {name: {'value': value} for name, value in self.console.values.items()}
        self.factory = patch('dolly.follow_capabilities.FollowCapabilityMonitor', return_value=self.monitor)
        self.camera = patch('dolly.replay_camera.ReplayCameraMonitor.sample', return_value={'ready': True})
        self.factory.start()
        self.camera.start()
        self.addCleanup(self.factory.stop)
        self.addCleanup(self.camera.stop)

    def test_preview_keeps_game_camera_and_f8_does_not_enter_flight(self):
        self.c.start_game_follow(FollowSettings(distance=200, shoulder=40, height=15))
        self.assertTrue(self.c._follow_active)
        self.assertFalse(self.c._native_active)
        app = SimpleNamespace(controller=self.c, busy=False,
                              _submit=lambda _label, function: function())
        with patch.object(self.c, 'enter_native_flight') as flight:
            editor_session.dispatch(app, {'action': 'panel', 'value': 1}, self.bridge)
        flight.assert_not_called()
        self.assertEqual(self.bridge.owner, 'panel')

    def test_f9_restores_rig_before_game_input(self):
        self.c.start_game_follow(FollowSettings())
        self.c.toggle_game_ui(True)
        self.assertFalse(self.c._follow_active)
        self.assertEqual(self.console.values[ENABLED], self.originals[ENABLED])
        for name in BOUNDS:
            self.assertEqual(self.console.values[PREFIX + name], self.originals[PREFIX + name])
        self.monitor.close.assert_called_once()
        self.assertEqual(self.bridge.owner, 'game_ui')

    def test_free_flight_restores_rig_first(self):
        self.c.start_game_follow(FollowSettings(distance=250))
        self.c.enter_native_flight()
        self.assertFalse(self.c._follow_active)
        self.assertTrue(self.c._native_manual)
        self.assertEqual(self.console.values[PREFIX + 'x_offset'], self.originals[PREFIX + 'x_offset'])

    def test_unselected_unpaused_or_competing_camera_never_writes(self):
        for field, value in (('_game_ui_visible', False), ('_native_active', True),
                             ('_native_manual', True)):
            with self.subTest(field=field):
                setattr(self.c, field, value)
                with self.assertRaises(RuntimeError):
                    self.c.start_game_follow(FollowSettings())
                setattr(self.c, field, not value)
                self.assertFalse(self.c._follow_active)
        self.console.values['citadel_spectator_mode'] = 1
        with self.assertRaisesRegex(RuntimeError, 'Hero Chase'):
            self.c.start_game_follow(FollowSettings())
        self.assertEqual(self.console.values[ENABLED], 0)

    def test_unsupported_capabilities_fail_before_mutation(self):
        self.monitor.sample.side_effect = RuntimeError('wrong type')
        with self.assertRaisesRegex(RuntimeError, 'wrong type'):
            self.c.start_game_follow(FollowSettings())
        self.assertEqual(self.console.values, self.originals)
        self.monitor.close.assert_called_once()

    def test_changed_session_retains_snapshot_and_blocks_new_camera(self):
        self.c.start_game_follow(FollowSettings())
        self.c._session = SimpleNamespace()
        with self.assertRaisesRegex(RuntimeError, 'different replay session'):
            self.c.stop()
        self.assertFalse(self.c._follow_active)
        self.assertTrue(self.c._follow_transaction.originals)
        self.monitor.close.assert_not_called()

    def test_stop_restores_even_after_stock_camera_type_changes(self):
        self.c.start_game_follow(FollowSettings())
        with patch('dolly.replay_camera.ReplayCameraMonitor.sample', side_effect=AssertionError('not an exit gate')):
            self.c.stop()
        self.assertFalse(self.c._follow_active)
        self.assertIsNone(self.c._follow_transaction)
        self.assertEqual(self.console.values[ENABLED], 0)

    def test_rollback_can_restore_after_replay_exits_in_same_owned_process(self):
        self.c.start_game_follow(FollowSettings())
        self.c._demo = Path('/chosen/other.dem')
        with patch.object(self.c, '_require_demo', side_effect=RuntimeError('no replay')):
            self.c.stop_game_follow()
        self.assertIsNone(self.c._follow_transaction)
        self.assertEqual(self.console.values[ENABLED], self.originals[ENABLED])
        self.assertEqual(self.console.values[PREFIX + 'x_offset'], self.originals[PREFIX + 'x_offset'])

    def test_update_rechecks_camera_readiness_without_mutating(self):
        self.c.start_game_follow(FollowSettings())
        before = dict(self.console.values)
        with patch('dolly.replay_camera.ReplayCameraMonitor.sample', return_value={'ready': False}):
            with self.assertRaisesRegex(RuntimeError, 'normal camera'):
                self.c.start_game_follow(FollowSettings(distance=300))
        self.assertEqual(self.console.values, before)
        self.assertTrue(self.c._follow_active)
        self.c.stop_game_follow()
