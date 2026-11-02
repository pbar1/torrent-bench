"""A stalled transfer must never be reported as a completed payload rate."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from api import Qbit
from run import Benchmark, TransferTimeout, transfer_details, verify


class ResultsTest(unittest.TestCase):
    def test_progress_reset_does_not_become_a_transfer_or_startup_rate(self):
        result = transfer_details([(0.01, 600), (0.2, 10), (1, 1000)], 1000)
        self.assertFalse(result['progress_monotonic'])
        self.assertIsNone(result['active_10_90_mib_s'])
        self.assertIsNone(result['first_observed_payload_s'])
        self.assertEqual(result['progress_samples'], [[0.01, 600], [0.2, 10], [1, 1000]])

    def test_completed_pieces_do_not_finish_a_torrent_that_is_still_moving(self):
        client = Qbit()
        rows = [{'hash': str(i), 'progress': 1, 'completed': 1024, 'state': state}
                for i, state in enumerate(('moving', 'downloading', 'stalledUP'))]
        with patch.object(client, 'call', return_value=rows):
            self.assertEqual([row['done'] for row in client.status()], [False, False, True])

    def test_deferred_write_is_rechecked_and_disclosed(self):
        good = {'files': 1, 'bytes': 1024, 'sha256': 'all matched'}
        with patch('run.verify_once', side_effect=[AssertionError('pending write'), good]), \
                patch('run.time.sleep'):
            result = verify([], 'test-client')
        self.assertEqual(result['attempts'], 2)
        self.assertEqual(result['initial_error'], 'pending write')
        self.assertEqual(result['sha256'], 'all matched')

    def test_persistent_mismatch_is_not_accepted(self):
        with patch('run.verify_once', side_effect=AssertionError('bad bytes')), \
                patch('run.time.monotonic', side_effect=[0, 31]):
            with self.assertRaisesRegex(AssertionError, 'bad bytes'):
                verify([], 'test-client')

    def test_partial_upload_retains_evidence_without_a_completion_rate(self):
        with tempfile.TemporaryDirectory() as directory, patch('run.Meter') as meter:
            meter.return_value.finish.return_value = {'client': {'peak_anon_mib': 1}}
            bench = Benchmark.__new__(Benchmark)
            bench.ids = {'leech1': 'one', 'leech2': 'two'}
            bench.output = Path(directory)
            bench.results = []

            def stalled():
                raise TransferTimeout({'reason': 'stalled', 'verified_payload_bytes': 16384})

            result = bench.measured('test-client', 0, 'upload-2-peers', stalled, 8 * 1024 ** 3)
            self.assertEqual(result['status'], 'timeout')
            self.assertIsNone(result['mib_s'])
            self.assertEqual(result['details']['verified_payload_bytes'], 16384)
            saved = json.loads((bench.output / 'trials.json').read_text())
            self.assertEqual(saved[0]['status'], 'timeout')


if __name__ == '__main__':
    unittest.main()
