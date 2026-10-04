"""Layer scheduling and recovery contracts without renderer or recording work."""
import unittest
from unittest.mock import Mock

from dolly.ui.layer_pipeline import LayerPipeline, recover_export_failure


class LayerPipelineTests(unittest.TestCase):
    def ports(self):
        return {name: Mock() for name in ('recorder_active', 'submit', 'finish_capture', 'combine',
                                          'start_next', 'complete', 'audit', 'restore')}

    def test_busy_defers_capture_without_consuming_state(self):
        state = LayerPipeline(advance_pending=True, pending_capture='players')
        ports = self.ports()
        state.advance(busy=True, **ports)
        self.assertEqual(state.pending_capture, 'players')
        self.assertTrue(state.advance_pending)
        for port in ports.values(): port.assert_not_called()

    def test_capture_precedes_combine_and_take_and_keeps_completion_identity(self):
        state = LayerPipeline(advance_pending=True, pending_capture='players',
                              pending_combine='effects', queue=[('world', 'black')])
        ports = self.ports(); state.advance(busy=False, **ports)
        label, work, completion = ports['submit'].call_args.args
        self.assertEqual(label, 'Building players layer')
        self.assertIs(completion, ports['complete'])
        ports['finish_capture'].assert_not_called()
        work(); ports['finish_capture'].assert_called_once_with('players')
        self.assertIsNone(state.pending_capture)
        self.assertEqual(state.pending_combine, 'effects')
        self.assertEqual(state.queue, [('world', 'black')])
        self.assertFalse(state.advance_pending)
        ports['recorder_active'].assert_not_called()

    def test_active_recorder_blocks_next_take_without_consuming_queue(self):
        state = LayerPipeline(advance_pending=True, queue=[('effects', 'white')])
        ports = self.ports(); ports['recorder_active'].return_value = True
        state.advance(busy=False, **ports)
        ports['submit'].assert_not_called(); self.assertTrue(state.advance_pending)
        ports['recorder_active'].return_value = False
        state.advance(busy=False, **ports)
        ports['submit'].assert_called_once_with('Recording layer take', ports['start_next'], ports['complete'])
        self.assertEqual(state.queue, [('effects', 'white')])
        self.assertFalse(state.advance_pending)

    def test_final_audit_occurs_before_state_clear_and_restore_submission(self):
        base = object(); state = LayerPipeline(advance_pending=True, base_capture=base)
        ports = self.ports(); order = []
        ports['audit'].side_effect = lambda value: order.append(('audit', value, state.base_capture))
        ports['submit'].side_effect = lambda *args: order.append(('submit', state.base_capture))
        state.advance(busy=False, **ports)
        self.assertEqual(order, [('audit', base, base), ('submit', None)])
        self.assertFalse(state.advance_pending)
        label, work, complete = ports['submit'].call_args.args
        self.assertEqual(label, 'Restoring scene layers'); self.assertIs(work, ports['restore'])
        self.assertIsNone(complete(None))

    def test_completion_marks_capture_or_white_pass_and_failure_retains_auto_play_policy(self):
        for kind, field in (('capture', 'pending_capture'), ('white', 'pending_combine')):
            with self.subTest(kind=kind):
                state = LayerPipeline(active_take=('players', kind), pending_auto_play=True)
                self.assertFalse(state.completed({}))
                self.assertEqual(getattr(state, field), 'players')
                self.assertTrue(state.advance_pending); self.assertIsNone(state.active_take)
                state.failed()
                self.assertTrue(state.pending_auto_play)
                self.assertFalse(state.advance_pending)
                self.assertIsNone(getattr(state, field))
                state.clear()
                self.assertFalse(state.pending_auto_play)

    def test_recovery_continues_in_order_after_each_failure(self):
        order = []
        def failure(name):
            def run():
                order.append(name); raise ValueError(name)
            return run
        recover_export_failure(failure('recording'), failure('camera'), failure('scene'))
        self.assertEqual(order, ['recording', 'camera', 'scene'])
