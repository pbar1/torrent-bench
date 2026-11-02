"""Audit a complete comparison against its fixtures and sampled transfer evidence."""
import argparse
import collections
import gzip
import itertools
import json
from pathlib import Path

from assemble_results import CLIENTS, PHASES, key


def validate(path, repeats=3):
    trials = json.loads((path / 'trials.json').read_text())
    complete = json.loads((path / 'complete.json').read_text())
    assert complete['ok'] and not complete['timeouts']
    assert len(trials) == complete['trials'] == len(CLIENTS) * repeats * len(PHASES)
    assert {key(t) for t in trials} == set(itertools.product(CLIENTS, range(repeats), PHASES))
    fixtures = json.loads((path / 'fixtures-manifest.json').read_text())
    groups = collections.defaultdict(list)
    for fixture in fixtures:
        groups[fixture['group']].append(fixture)
    downloads = uploads = rechecks = checked_files = 0
    down_bytes = up_bytes = 0
    for trial in trials:
        assert trial['status'] == 'ok' and trial['elapsed_s'] > 0
        for process in ('client', 'peer1', 'peer2'):
            assert all(value >= 0 for value in trial['metrics'][process].values())
        workload = trial['workload']
        if trial['payload_bytes']:
            expected_rate = trial['payload_bytes'] / 1024 ** 2 / trial['elapsed_s']
            assert abs(trial['mib_s'] - expected_rate) < 1e-8
        if workload.startswith('download-'):
            fixtures_for_trial = groups[workload.removeprefix('download-')]
            expected_bytes = sum(t['bytes'] for t in fixtures_for_trial)
            expected_files = sum(len(t['files']) for t in fixtures_for_trial)
            assert trial['payload_bytes'] == expected_bytes
            assert trial['verification']['sha256'] == 'all matched'
            assert trial['verification']['bytes'] == expected_bytes
            assert trial['verification']['files'] == expected_files
            assert trial['details']['completed_torrents'] == len(fixtures_for_trial)
            assert trial['metrics']['client']['network_rx'] >= expected_bytes
            checked_files += expected_files
            down_bytes += expected_bytes
            downloads += 1
        elif workload == 'upload-2-peers':
            large = groups['large'][0]['bytes']
            assert trial['payload_bytes'] == 2 * large
            assert trial['metrics']['client']['network_tx'] >= 2 * large
            assert len(trial['details']['leechers']) == 2
            for peer in trial['details']['leechers']:
                assert peer['done'] == peer['count'] == 1
                assert peer['bytes'] == large and peer['downloaded'] >= large
                assert peer['uploaded'] == peer['failed_bytes'] == 0
                assert not peer['errors']
            up_bytes += trial['payload_bytes']
            uploads += 1
        elif workload == 'recheck-large':
            assert trial['details']['observed_checking']
            rechecks += 1
        elif workload == 'add-1000-paused':
            assert trial['details']['registered_torrents'] == 1000
            assert sum(trial['details']['states'].values()) == 1000

    samples = collections.Counter()
    last_time = {}
    plain = path / 'samples.jsonl'
    with (plain.open() if plain.exists() else gzip.open(path / 'samples.jsonl.gz', 'rt')) as stream:
        for line in stream:
            sample = json.loads(line)
            assert 'error' not in sample
            tag = key(sample['trial'])
            assert sample['time'] > last_time.get(tag, -1)
            last_time[tag] = sample['time']
            samples[tag] += 1
    assert set(samples) == {key(t) for t in trials}
    assert all(samples[key(t)] == t['metrics']['samples'] for t in trials)
    result = {'ok': True, 'phases': len(trials), 'download_phases': downloads,
              'upload_phases': uploads, 'independent_leecher_completions': 2 * uploads,
              'observed_rechecks': rechecks, 'sha256_checked_files': checked_files,
              'download_gib': down_bytes / 1024 ** 3, 'upload_gib': up_bytes / 1024 ** 3,
              'payload_gib': (down_bytes + up_bytes) / 1024 ** 3,
              'resource_samples': sum(samples.values()),
              'transfer_evidence': 'Every download RX and upload TX exceeds its full payload; every leecher received a complete payload and uploaded zero bytes.'}
    (path / 'validation.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    parser.add_argument('--repeats', type=int, default=3)
    args = parser.parse_args()
    print(json.dumps(validate(args.directory, args.repeats), indent=2))
