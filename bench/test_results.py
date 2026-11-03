"""A stalled transfer must never be reported as a completed payload rate."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from api import Aria2, Qbit
from run import Benchmark, TransferTimeout, transfer_details, verify


class ResultsTest(unittest.TestCase):
    def test_aria2_recheck_accepts_a_complete_terminal_result_and_discards_resume(self):
        client = Aria2()
        client.gids = {'hash': 'old'}
        torrent = {'hash': 'hash', 'files': [{'path': 'large.bin'}]}
        with tempfile.TemporaryDirectory() as directory:
            sidecar = Path(directory) / 'large.bin.aria2'
            sidecar.write_bytes(b'cached complete pieces')
            with patch.object(client, 'rpc', side_effect=['old', {'status': 'complete'}, 'OK']), \
                    patch('api.Path', return_value=sidecar), patch.object(client, 'add') as add:
                client.recheck(torrent)
            self.assertFalse(sidecar.exists())
            add.assert_called_once_with(torrent, check=True)

    def test_aria2_hash_check_does_not_look_like_a_complete_seed(self):
        client = Aria2()
        client.gids = {'hash': 'current'}
        row = {'gid': 'current', 'infoHash': 'hash', 'status': 'active',
               'totalLength': '1024', 'completedLength': '1024'}
        with patch.object(client, 'rpc', return_value=[[[{**row, 'verifiedLength': '0'}]], [[]], [[]]]):
            status = client.status()[0]
        self.assertTrue(status['checking'])
        self.assertFalse(status['done'])
        with patch.object(client, 'rpc', return_value=[[[row]], [[]], [[]]]):
            self.assertTrue(client.status()[0]['done'])

    def test_aria2_removed_gid_cannot_override_its_readded_torrent(self):
        client = Aria2()
        client.gids = {'hash': 'current'}
        paused = {'gid': 'current', 'infoHash': 'hash', 'status': 'paused',
                  'totalLength': '1024', 'completedLength': '0'}
        removed = {**paused, 'gid': 'old', 'status': 'removed'}
        with patch.object(client, 'rpc', return_value=[[[]], [[paused]], [[removed]]]):
            statuses = client.status()
        self.assertEqual(len(statuses), 1)
        self.assertTrue(statuses[0]['paused'])
        self.assertFalse(statuses[0]['done'])

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
