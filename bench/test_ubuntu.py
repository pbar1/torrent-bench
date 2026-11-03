"""Verify public-mode isolation, single-payload cleanup, and pinned metadata."""
import hashlib
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from run import Meter
from ubuntu_run import balanced_orders, clear_payload
from public_diagnostics import families


class UbuntuTest(unittest.TestCase):
    def test_peer_family_counts_do_not_expose_addresses(self):
        result = families(['192.0.2.1:6881', '[2001:db8::1]:6881', '2001:db8::2', 'unknown'])
        self.assertEqual(result, {'ipv4': 1, 'ipv6': 2, 'unknown': 1})
        self.assertNotIn('192.0.2.1', json.dumps(result))

    def test_six_rounds_balance_positions_and_directed_carryover(self):
        clients = ['q', 'd', 't', 'rt', 'rq', 'a']
        orders = balanced_orders(clients, 6, 20261103)
        self.assertEqual(orders, balanced_orders(clients, 6, 20261103))
        for order in orders:
            self.assertEqual(set(order), set(clients))
        for column in zip(*orders):
            self.assertEqual(set(column), set(clients))
        pairs = Counter(pair for order in orders for pair in zip(order, order[1:]))
        self.assertEqual(len(pairs), 30)
        self.assertEqual(set(pairs.values()), {1})

    def test_payload_and_resume_data_are_removed(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            (path / 'ubuntu.iso').write_bytes(b'payload')
            (path / 'ubuntu.iso.aria2').write_bytes(b'resume')
            (path / 'nested').mkdir()
            (path / 'nested/file').write_bytes(b'more')
            result = clear_payload(path)
            self.assertEqual(list(path.iterdir()), [])
            self.assertFalse(result['iso_retained'])
            self.assertEqual(result['remaining_entries'], 0)

    def test_public_meter_never_accesses_reference_peers(self):
        meter = Meter({'aria2': 'only-client'}, 'aria2', Path('/tmp'), reference_peers=False)
        with patch('run.snapshot', return_value={'cpu_s': 1}) as snapshot:
            meter.collect()
        snapshot.assert_called_once_with('only-client')
        self.assertEqual(set(meter.samples[0]), {'time', 'client'})

    def test_synthetic_meter_still_collects_both_reference_peers(self):
        meter = Meter({'aria2': 'client', 'peer1': 'seed1', 'peer2': 'seed2'}, 'aria2', Path('/tmp'))
        with patch('run.snapshot', return_value={'cpu_s': 1}):
            meter.collect()
        self.assertEqual(set(meter.samples[0]), {'time', 'client', 'peer1', 'peer2'})

    def test_torrent_metadata_is_pinned(self):
        root = Path('/fixtures') if Path('/fixtures/source.json').exists() else Path(__file__).resolve().parents[1] / 'ubuntu'
        source = json.loads((root / 'source.json').read_text())
        raw = (root / 'torrents/ubuntu.torrent').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), source['torrent_sha256'])
        manifest = json.loads((root / 'manifest.json').read_text())
        self.assertEqual(manifest[0]['files'][0]['sha256'], source['iso_sha256'])
        self.assertEqual(manifest[0]['bytes'], source['payload_bytes'])
        self.assertNotIn(b'url-list', raw)
        self.assertNotIn(b'httpseeds', raw)


if __name__ == '__main__':
    unittest.main()
