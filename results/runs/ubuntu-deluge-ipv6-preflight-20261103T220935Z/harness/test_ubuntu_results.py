"""Reject public results with missing evidence or failed payload cleanup."""
import json
import tempfile
import unittest
from pathlib import Path

from summarize_ubuntu import MIB, audit


class PublicResultsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.source = {'payload_bytes': MIB, 'iso_sha256': 'expected'}
        self.environment = {'arguments': {'clients': ['aria2'], 'repeats': 1},
                            'public_network': {'internal': False},
                            'containers': {'aria2': {'host_config': {
                                'NanoCpus': 2_000_000_000,
                                'Memory': 1536 * MIB, 'MemorySwap': 1536 * MIB}}}}
        self.tag = {'client': 'aria2', 'repeat': 0, 'workload': 'ubuntu-public'}
        self.trial = {**self.tag, 'status': 'ok', 'payload_bytes': MIB, 'elapsed_s': 2,
                      'mib_s': 0.5, 'utc_start': '2026-11-03T00:00:00Z',
                      'utc_end': '2026-11-03T00:00:03Z',
                      'cleanup': {'remaining_entries': 0, 'iso_retained': False},
                      'verification': {'sha256': 'all matched', 'files': 1, 'bytes': MIB},
                      'details': {'completed_torrents': 1},
                      'metrics': {'samples': 2, 'measurement_s': 2,
                                  'client': {'network_rx': MIB}}}
        inputs = {'complete.json': {'ok': True, 'trials': 1, 'scratch_empty': True},
                  'fixtures-manifest.json': [{'bytes': MIB, 'files': [{'sha256': 'expected'}]}],
                  'torrent-source.json': self.source, 'trials.json': [self.trial]}
        for name, value in inputs.items():
            (self.path / name).write_text(json.dumps(value))
        sample = {'trial': self.tag, 'time': 1, 'client': {}}
        (self.path / 'samples.jsonl').write_text((json.dumps(sample) + '\n') * 2)

    def check(self):
        return audit(self.path, [self.trial], self.environment, self.source)

    def test_complete_download_is_counted(self):
        self.assertEqual(self.check()['verified_payload_bytes'], MIB)

    def test_retained_iso_is_rejected(self):
        self.trial['cleanup']['iso_retained'] = True
        with self.assertRaises(AssertionError):
            self.check()

    def test_missing_resource_sample_is_rejected(self):
        self.trial['metrics']['samples'] = 3
        with self.assertRaises(AssertionError):
            self.check()

    def test_timeout_never_receives_full_file_rate(self):
        self.trial['status'] = 'timeout'
        with self.assertRaises(AssertionError):
            self.check()
        self.trial['mib_s'] = None
        self.assertEqual(self.check()['completed_downloads'], 0)


if __name__ == '__main__':
    unittest.main()
