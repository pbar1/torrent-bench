"""Summarize successful trials without discarding variation or raw evidence."""
import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

CLIENTS = ['qbittorrent', 'deluge', 'transmission', 'rtorrent', 'rqbit', 'aria2']
WORKLOADS = ['download-large', 'download-files', 'download-concurrent', 'download-shaped',
             'upload-2-peers', 'recheck-large', 'idle-empty', 'idle-64-seeds',
             'add-1000-paused', 'idle-1000-paused']


def summarize(path):
    trials = json.loads((path / 'trials.json').read_text())
    complete = json.loads((path / 'complete.json').read_text())
    assert complete['ok'] and complete['trials'] == len(trials)
    groups = defaultdict(list)
    for trial in trials:
        groups[(trial['client'], trial['workload'])].append(trial)
    rows = []
    for (client, workload), items in groups.items():
        times = [t['elapsed_s'] for t in items]
        rates = [t['mib_s'] for t in items if t['mib_s'] is not None]
        active = [t['details']['active_10_90_mib_s'] for t in items
                  if isinstance(t['details'], dict) and t['details'].get('active_10_90_mib_s') is not None]
        startup = [t['details']['first_observed_payload_s'] for t in items
                   if isinstance(t['details'], dict) and t['details'].get('first_observed_payload_s') is not None]
        timeouts = sum(t.get('status', 'ok') != 'ok' for t in items)
        rows.append({'client': client, 'workload': workload, 'n': len(items),
                     'completed': len(items) - timeouts, 'timeouts': timeouts,
                     'median_s': statistics.median(times), 'min_s': min(times), 'max_s': max(times),
                     'median_mib_s': statistics.median(rates) if rates else '',
                     'min_mib_s': min(rates) if rates else '', 'max_mib_s': max(rates) if rates else '',
                     'median_active_10_90_mib_s': statistics.median(active) if active else '',
                     'median_first_payload_s': statistics.median(startup) if startup else '',
                     'median_cpu_s': statistics.median(t['metrics']['client']['cpu_s'] for t in items),
                     'median_rss_mib': statistics.median(t['metrics']['client']['median_rss_mib'] for t in items),
                     'peak_rss_mib': max(t['metrics']['client']['peak_rss_mib'] for t in items),
                     'peak_anon_mib': max(t['metrics']['client']['peak_anon_mib'] for t in items),
                     'peak_container_mib': max(t['metrics']['client']['peak_memory_mib'] for t in items),
                     'peak_working_mib': max(t['metrics']['client']['peak_working_mib'] for t in items),
                     'peak_peer_cpu_pct': max(t['metrics'][p]['cpu_pct_one_core'] for t in items for p in ['peer1', 'peer2'])})
    with (path / 'summary.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    lines = ['# Measured results', '',
             'Rates are MiB/s; values are the median across repetitions. '
             'Min–max ranges and all CPU/memory counters are in `summary.csv` and `trials.json`.', '']
    lookup = {(r['client'], r['workload']): r for r in rows}
    clients = [c for c in CLIENTS if any(k[0] == c for k in groups)]
    lines += ['| Client | 4 GiB down | 2,048 files | 64 torrents | Capped down | 2-peer upload | Recheck |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for client in clients:
        values = []
        for workload in WORKLOADS[:6]:
            r = lookup.get((client, workload), {})
            value = r.get('median_mib_s', '')
            label = f'{value:.1f}' if value != '' else '—'
            if r.get('timeouts'):
                label += f' ({r["completed"]}/{r["n"]} completed)'
            values.append(label)
        lines.append('| ' + client + ' | ' + ' | '.join(values) + ' |')
    lines += ['', 'Transfer rate between the first samples at or above 10% and 90% of the payload. '
              'This reduces startup/completion effects; very short transfers may not have enough samples.', '',
              '| Client | Large active rate | Large first payload, s | Upload active rate | Upload first payload, s | Capped active rate |',
              '|---|---:|---:|---:|---:|---:|']
    for client in clients:
        values = [lookup.get((client, w), {}).get(field, '') for w, field in [
            ('download-large', 'median_active_10_90_mib_s'), ('download-large', 'median_first_payload_s'),
            ('upload-2-peers', 'median_active_10_90_mib_s'), ('upload-2-peers', 'median_first_payload_s'),
            ('download-shaped', 'median_active_10_90_mib_s')]]
        lines.append('| ' + client + ' | ' + ' | '.join(f'{v:.1f}' if v != '' else '—' for v in values) + ' |')
    lines += ['', 'Memory in MiB. RSS includes mapped/shared pages; container total includes charged disk cache.', '',
              '| Client | Empty idle RSS | 64 seeds idle RSS | 1,000 paused idle RSS | Highest sampled RSS | Highest anonymous | Highest container total |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for client in clients:
        idle = [lookup.get((client, w), {}).get('median_rss_mib', '')
                for w in ['idle-empty', 'idle-64-seeds', 'idle-1000-paused']]
        active = [r for r in rows if r['client'] == client]
        values = idle + [max(r[field] for r in active) for field in
                         ['peak_rss_mib', 'peak_anon_mib', 'peak_container_mib']]
        lines.append('| ' + client + ' | ' + ' | '.join(f'{v:.1f}' if v != '' else '—' for v in values) + ' |')
    lines += ['', '| Client | Workload | n | Wall time median (min–max), s | CPU median, core-seconds | Peak RSS, MiB |',
              '|---|---|---:|---:|---:|---:|']
    for client in clients:
        for workload in WORKLOADS:
            r = lookup.get((client, workload))
            if r:
                lines.append(f'| {client} | {workload} | {r["n"]} | '
                             f'{r["median_s"]:.2f} ({r["min_s"]:.2f}–{r["max_s"]:.2f}) | '
                             f'{r["median_cpu_s"]:.2f} | {r["peak_rss_mib"]:.1f} |')
    (path / 'SUMMARY.md').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines[:len(clients) + 8]))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    summarize(parser.parse_args().directory)
