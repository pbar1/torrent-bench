"""Assemble the measured November 2026 comparison with explicit provenance.

Keep unaffected baseline cases, replace every qBittorrent case after monitor
fixes, and add the separately completed final Deluge repeat. No fastest-run
selection is performed. Future full runs need no assembly step.
"""
import argparse
import gzip
import itertools
import json
import shutil
from pathlib import Path

from run import transfer_details

CLIENTS = ['qbittorrent', 'deluge', 'transmission', 'rtorrent', 'rqbit']
PHASES = ['idle-empty', 'download-large', 'recheck-large', 'upload-2-peers',
          'download-files', 'download-concurrent', 'idle-64-seeds',
          'download-shaped', 'add-1000-paused', 'idle-1000-paused']


def key(row):
    return row['client'], row['repeat'], row['workload']


def assemble(baseline, corrected, remainder, output, aria2=None):
    sources = {'baseline': baseline, 'qbittorrent-corrected': corrected,
               'deluge-final-repeat': remainder}
    clients = list(CLIENTS)
    if aria2 is not None:
        sources['aria2'] = aria2
        clients.append('aria2')
    for folder in [corrected, remainder] + ([aria2] if aria2 is not None else []):
        assert json.loads((folder / 'complete.json').read_text())['ok']
    manifest = (baseline / 'fixtures-manifest.json').read_bytes()
    environments = {}
    selected = {}
    excluded = []
    for label, folder in sources.items():
        assert (folder / 'fixtures-manifest.json').read_bytes() == manifest
        environments[label] = json.loads((folder / 'environment.json').read_text())
        for row in json.loads((folder / 'trials.json').read_text()):
            if label == 'baseline' and row['client'] == 'qbittorrent':
                excluded.append(key(row))
                continue
            if label == 'qbittorrent-corrected':
                assert row['client'] == 'qbittorrent'
            if label == 'deluge-final-repeat':
                assert row['client'] == 'deluge' and row['repeat'] == 2
            if label == 'aria2':
                assert row['client'] == 'aria2'
            assert key(row) not in selected
            assert row['status'] == 'ok'
            if row['workload'].startswith('download-'):
                assert row['verification']['sha256'] == 'all matched'
            if row['workload'] == 'recheck-large':
                assert row['details']['observed_checking']
            if isinstance(row['details'], dict) and 'progress_samples' in row['details']:
                row['details'] = {**row['details'], **transfer_details(
                    row['details']['progress_samples'], row['payload_bytes'])}
            selected[key(row)] = {**row, 'source_run': label}
    assert set(selected) == set(itertools.product(clients, range(3), PHASES))
    for env in environments.values():
        for field in ('NCPU', 'MemTotal', 'KernelVersion', 'Architecture', 'ServerVersion', 'Driver', 'CgroupVersion'):
            assert env[field] == environments['baseline'][field]
        for client in CLIENTS:
            assert env['containers'][client]['host_config'] == environments['baseline']['containers'][client]['host_config']
            assert env['containers'][client]['image_ref'] == environments['baseline']['containers'][client]['image_ref']
    if aria2 is not None:
        assert environments['aria2']['containers']['aria2']['host_config'] == environments['baseline']['containers']['qbittorrent']['host_config']
    rows = [selected[k] for k in itertools.product(clients, range(3), PHASES)]
    output.mkdir(parents=True, exist_ok=False)
    (output / 'trials.json').write_text(json.dumps(rows, indent=2) + '\n')
    (output / 'environment.json').write_text(json.dumps({'source_runs': environments}, indent=2) + '\n')
    (output / 'selection.json').write_text(json.dumps({
        'rule': 'Keep baseline non-qBittorrent cases; replace all qBittorrent cases; add Deluge repeat 2.'
                + (' Add all three aria2 repetitions from the later extension run.' if aria2 is not None else ''),
        'reason': 'Require observed recheck state and seed-ready completion; tolerate and disclose deferred disk writes.',
        'derived_metric_policy': 'Recompute progress diagnostics from retained samples; suppress startup/active rates if progress resets. Wall times, payload rates and resource counters are unchanged.',
        'source_directories': {label: str(folder) for label, folder in sources.items()},
        'excluded_baseline_keys': excluded}, indent=2) + '\n')
    with (output / 'samples.jsonl').open('w') as dest:
        for label, folder in sources.items():
            plain = folder / 'samples.jsonl'
            with (plain.open() if plain.exists() else gzip.open(folder / 'samples.jsonl.gz', 'rt')) as src:
                for line in src:
                    row = json.loads(line)
                    chosen = selected.get(key(row['trial']))
                    if chosen and chosen['source_run'] == label:
                        dest.write(json.dumps({**row, 'source_run': label}) + '\n')
    for client in clients:
        folder = aria2 if client == 'aria2' else corrected if client == 'qbittorrent' else remainder if client == 'deluge' else baseline
        filename = client + '-effective-settings.json'
        shutil.copyfile(folder / filename, output / filename)
    (output / 'fixtures-manifest.json').write_bytes(manifest)
    (output / 'complete.json').write_text(json.dumps({'ok': True, 'trials': len(rows), 'timeouts': []}, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for arg in ('baseline', 'corrected', 'remainder', 'output'):
        parser.add_argument(arg, type=Path)
    parser.add_argument('--aria2-run', type=Path)
    args = parser.parse_args()
    assemble(args.baseline, args.corrected, args.remainder, args.output, args.aria2_run)
