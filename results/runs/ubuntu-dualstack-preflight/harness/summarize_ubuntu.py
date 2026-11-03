"""Audit and summarize the separately opted-in public Ubuntu trials."""
import argparse
import csv
import gzip
import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path

MIB = 1024 ** 2


def audit(path, trials, environment, source):
    complete = json.loads((path / 'complete.json').read_text())
    clients = environment['arguments']['clients']
    repeats = environment['arguments']['repeats']
    expected = {(c, r, 'ubuntu-public') for c in clients for r in range(repeats)}
    key = lambda t: (t['client'], t['repeat'], t['workload'])
    assert complete['ok'] and complete['trials'] == len(trials)
    assert len(trials) == len(expected) and {key(t) for t in trials} == expected
    assert complete['scratch_empty']
    assert not environment['public_network']['internal']
    manifest = json.loads((path / 'fixtures-manifest.json').read_text())
    assert manifest[0]['bytes'] == source['payload_bytes']
    assert manifest[0]['files'][0]['sha256'] == source['iso_sha256']
    successful = [t for t in trials if t['status'] == 'ok']
    for t in trials:
        assert t['status'] in ('ok', 'timeout', 'error')
        assert t['payload_bytes'] == source['payload_bytes']
        assert t['cleanup']['remaining_entries'] == 0 and not t['cleanup']['iso_retained']
        assert t['utc_start'] < t['utc_end']
        assert set(t['metrics']) == {'client', 'samples', 'measurement_s'}
        assert t['metrics']['samples'] >= 2
        assert t['metrics']['client']['network_rx'] >= 0
        if t['status'] == 'ok':
            assert t['verification']['sha256'] == 'all matched'
            assert t['verification']['files'] == 1
            assert t['verification']['bytes'] == source['payload_bytes']
            assert t['details']['completed_torrents'] == 1
            assert t['metrics']['client']['network_rx'] >= source['payload_bytes']
            assert abs(t['mib_s'] - source['payload_bytes'] / MIB / t['elapsed_s']) < 1e-8
        else:
            assert t['mib_s'] is None
    for c in clients:
        config = environment['containers'][c]['host_config']
        assert config['NanoCpus'] == 2_000_000_000
        assert config['Memory'] == config['MemorySwap'] == 1536 * MIB
    sample_path = path / 'samples.jsonl.gz'
    opener = gzip.open
    if not sample_path.exists():
        sample_path, opener = path / 'samples.jsonl', open
    counts = Counter()
    with opener(sample_path, 'rt') as handle:
        for line in handle:
            sample = json.loads(line)
            assert set(sample) == {'trial', 'time', 'client'}
            counts[key(sample['trial'])] += 1
    assert counts == Counter({key(t): t['metrics']['samples'] for t in trials})
    assert not (path / 'failure.txt').exists()
    return {'ok': True, 'trials': len(trials), 'completed_downloads': len(successful),
            'all_downloads_completed': len(successful) == len(trials),
            'independent_sha256_checks': len(successful),
            'verified_payload_bytes': sum(t['verification']['bytes'] for t in successful),
            'resource_samples': sum(counts.values()), 'iso_retained': False,
            'cleanups_with_empty_scratch': len(trials),
            'input_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in
                             [path / 'trials.json', sample_path, path / 'torrent-source.json']}}


def summarize(path):
    trials = json.loads((path / 'trials.json').read_text())
    environment = json.loads((path / 'environment.json').read_text())
    source = json.loads((path / 'torrent-source.json').read_text())
    validation = audit(path, trials, environment, source)
    (path / 'validation.json').write_text(json.dumps(validation, indent=2) + '\n')
    rows = []
    for client in environment['arguments']['clients']:
        items = [t for t in trials if t['client'] == client]
        success = [t for t in items if t['status'] == 'ok']
        row = {'client': client, 'n': len(items), 'completed': len(success),
               'timeouts': sum(t['status'] == 'timeout' for t in items),
               'errors': sum(t['status'] == 'error' for t in items)}
        for field in ('elapsed_s', 'mib_s'):
            values = [t[field] for t in success]
            for prefix, fn in [('median', statistics.median), ('min', min), ('max', max)]:
                row[prefix + '_' + field] = fn(values) if values else ''
        for field in ('first_observed_payload_s', 'active_10_90_mib_s'):
            values = [t['details'][field] for t in success if t['details'].get(field) is not None]
            row['median_' + field] = statistics.median(values) if values else ''
        for field in ('cpu_s', 'network_rx', 'network_tx'):
            row['median_' + field] = statistics.median(t['metrics']['client'][field] for t in items)
        for field in ('rss_mib', 'anon_mib', 'memory_mib', 'working_mib'):
            row['peak_' + field] = max(t['metrics']['client']['peak_' + field] for t in items)
        rows.append(row)
    with (path / 'summary.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    lines = ['# Public Ubuntu fresh-download results', '',
             f"{environment['arguments']['repeats']} fresh attempt(s) per client, one ISO at a time. "
             'Rates include discovery and completion. '
             'Only completed, independently SHA-256 verified downloads receive a full-file rate. '
             'Memory peaks cover all attempts; charged memory includes disk cache. '
             'The ISO is deleted after every attempt.', '',
             '| Client | Completed | Median MiB/s | Min–max MiB/s | Median seconds | CPU core-seconds | Peak RSS MiB | Peak anonymous MiB | Peak charged MiB |',
             '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    number = lambda x: f'{x:.2f}' if x != '' else '—'
    for r in rows:
        values = [r['client'], f'{r["completed"]}/{r["n"]}', number(r['median_mib_s']),
                  number(r['min_mib_s']) + '–' + number(r['max_mib_s']), number(r['median_elapsed_s']),
                  number(r['median_cpu_s']), number(r['peak_rss_mib']),
                  number(r['peak_anon_mib']), number(r['peak_memory_mib'])]
        lines.append('| ' + ' | '.join(values) + ' |')
    lines += ['', 'The public swarm, ISP, peer mix, and network congestion are uncontrolled. '
              'These observations measure this host and time window, rather than each client’s maximum capacity. '
              'Docker uses IPv4 NAT without forwarded incoming ports. See `trials.json` for each repetition, '
              'startup/active-window diagnostics, upload traffic, verification, and cleanup; '
              '`validation.json` audits completeness and raw resource sample counts.', '']
    (path / 'SUMMARY.md').write_text('\n'.join(lines))
    print('\n'.join(lines))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    summarize(parser.parse_args().directory)
