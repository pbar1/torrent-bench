"""Analyze the registered, repeated public experiment without discarding failures.

Python's inclusive quartiles use linear interpolation at ranks (n - 1) * p.
Wilson intervals describe completion counts; the Internet trials are not assumed
to be independent samples of a stationary swarm. No significance test is used.
"""
import argparse
import csv
import datetime
import gzip
import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path

from summarize_ubuntu import audit


def distribution(values):
    values = sorted(values)
    if not values:
        return dict.fromkeys(('n', 'median', 'q1', 'q3', 'min', 'max', 'mean'), None) | {'n': 0}
    quartiles = statistics.quantiles(values, n=4, method='inclusive') if len(values) > 1 else values * 3
    return {'n': len(values), 'median': statistics.median(values),
            'q1': quartiles[0], 'q3': quartiles[2], 'min': values[0],
            'max': values[-1], 'mean': statistics.mean(values)}


def wilson(successes, total):
    z = 1.959963984540054
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    radius = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return [max(0, center - radius), min(1, center + radius)]


def summarize_client(items, deadline):
    completed = [t for t in items if t['status'] == 'ok']
    row = {'client': items[0]['client'], 'n': len(items), 'completed': len(completed),
           'status_counts': dict(Counter(t['status'] for t in items)),
           'completion_wilson95': wilson(len(completed), len(items)),
           'deadline_penalized_mean_s': statistics.mean(
               t['elapsed_s'] if t['status'] == 'ok' else deadline for t in items)}
    for field in ('elapsed_s', 'mib_s'):
        row[field] = distribution(t[field] for t in completed)
    for field in ('first_observed_payload_s', 'active_10_90_mib_s'):
        # These APIs can count initialization/hash-scan progress as bytes even
        # without a sampled decrease. Keep the original counters as evidence,
        # but do not interpret them as transferred payload.
        row[field] = distribution(t['details'][field] for t in completed
                                  if t['client'] not in ('rqbit', 'rtorrent')
                                  and t['details'].get(field) is not None)
    # Resource distributions include all attempts. Failed/partial attempts are
    # identified in the per-attempt table rather than silently thrown away.
    resources = ('cpu_s', 'network_rx', 'network_tx', 'peak_rss_mib',
                 'peak_anon_mib', 'peak_memory_mib', 'peak_working_mib')
    for field in resources:
        row[field] = distribution(t['metrics']['client'][field] for t in items)
    row['completed_resources'] = {
        field: distribution(t['metrics']['client'][field] for t in completed)
        for field in resources}
    row['status_poll_interval_s'] = distribution(
        b[0] - a[0] for t in items for a, b in zip(
            t['details'].get('progress_samples', []), t['details'].get('progress_samples', [])[1:]))
    discovery = [d for t in items for d in t['details'].get('discovery', [])]
    family_samples = [d['peer_families'] for d in discovery if 'peer_families' in d]
    row['discovery'] = {
        'samples': len(discovery),
        'errors': sum('diagnostic_error_type' in d for d in discovery),
        'address_family_samples': len(family_samples),
        'max_observed_ipv4_peers': max((d['ipv4'] for d in family_samples), default=None),
        'max_observed_ipv6_peers': max((d['ipv6'] for d in family_samples), default=None)}
    return row


def timestamp(value):
    return datetime.datetime.fromisoformat(value)


def audit_samples(trials, samples):
    groups = {}
    for sample in samples:
        key = (sample['trial']['client'], sample['trial']['repeat'])
        groups.setdefault(key, []).append(sample)
    intervals = {}
    for trial in trials:
        rows = groups[(trial['client'], trial['repeat'])]
        assert len(rows) == trial['metrics']['samples']
        gaps = [b['time'] - a['time'] for a, b in zip(rows, rows[1:])]
        assert gaps and min(gaps) > 0
        intervals.setdefault(trial['client'], []).extend(gaps)
        duration = rows[-1]['time'] - rows[0]['time']
        assert math.isclose(duration, trial['metrics']['measurement_s'])
        recorded = trial['metrics']['client']
        for field in ('memory_mib', 'working_mib', 'anon_mib', 'file_mib', 'rss_mib'):
            values = [row['client'][field] for row in rows]
            assert recorded['peak_' + field] == max(values)
            assert recorded['median_' + field] == statistics.median(values)
        for field in ('cpu_s', 'throttled_s', 'network_rx', 'network_tx', 'io_read', 'io_write'):
            assert recorded[field] == rows[-1]['client'][field] - rows[0]['client'][field]
    return {client: distribution(gaps) for client, gaps in intervals.items()}


def audit_diagnostics(trials):
    assert not any('diagnostic_error_type' in d for t in trials
                   for d in t['details'].get('discovery', [])), \
        'Optional diagnostic RPC errors can block the synchronous timing observer'


def audit_registered(path, trials, environment, source):
    audit_diagnostics(trials)
    validation = audit(path, trials, environment, source)
    protocol = json.loads((path / 'protocol.json').read_text())
    clients = environment['arguments']['clients']
    orders = protocol['orders']
    assert len(orders) == protocol['repeats'] == environment['arguments']['repeats']
    assert all(Counter(order) == Counter(clients) for order in orders)
    assert [(t['repeat'], t['client']) for t in trials] == [
        (r, client) for r, order in enumerate(orders) for client in order]
    assert timestamp(protocol['registered_utc']) <= min(timestamp(t['utc_start']) for t in trials)
    assert environment['arguments']['timeout'] == protocol['deadline_s']
    assert environment['arguments']['stall_seconds'] == 0
    assert protocol['early_no_progress_cutoff_s'] is None
    assert environment['public_network']['ipv6'] is True
    assert all(timestamp(a['utc_end']) <= timestamp(b['utc_start'])
               for a, b in zip(trials, trials[1:]))
    positions = Counter((client, position) for order in orders
                        for position, client in enumerate(order))
    transitions = Counter((a, b) for order in orders for a, b in zip(order, order[1:]))
    # This cohort uses one complete six-treatment Williams design. Boundaries
    # between rounds are excluded from the directed carryover balance claim.
    assert len(orders) == 6
    if len(clients) == 6:
        assert len(positions) == 36 and set(positions.values()) == {1}
        assert len(transitions) == 30 and set(transitions.values()) == {1}
        ordering_design = 'Six-client Williams; positions and within-round directed pairs balanced'
    else:
        assert clients == ['deluge'] and (path / 'study.json').exists()
        assert positions == Counter({('deluge', 0): 6}) and not transitions
        study = json.loads((path / 'study.json').read_text())
        assert study['planned_attempts'] == 6 and study['deadline_s'] == protocol['deadline_s']
        assert timestamp(study['registered_utc']) <= timestamp(trials[0]['utc_start'])
        native = (path / study['native_cohort']).resolve()
        assert hashlib.sha256((native / 'trials.json').read_bytes()).hexdigest() == study['native_trials_sha256']
        assert environment['containers']['deluge']['image_id'] == study['same_deluge_image_id']
        for name, sha in study['profile_sha256'].items():
            assert hashlib.sha256((path / 'profile' / name).read_bytes()).hexdigest() == sha
        evidence_path = path.parent / study['preflight']
        assert hashlib.sha256(evidence_path.read_bytes()).hexdigest() == study['preflight_sha256']
        evidence = json.loads(evidence_path.read_text())
        assert evidence['ok'] and evidence['port_6881_socket_entries']['tcp6'] > 0
        assert evidence['port_6881_socket_entries']['udp6'] > 0
        assert evidence['listen_interface'] == study['listen_interface']
        for t in trials:
            settings = json.loads((path / t['settings']['file']).read_text())
            # The archived init script selects the default route on each start.
            # Docker can rename that interface between starts; the preflight's
            # literal ethN name is an observation, not the treatment definition.
            interface = settings['preferences']['listen_interface']
            assert interface.startswith('eth') and interface[3:].isdigit()
            discovery = t['details']['discovery']
            assert discovery and all(d.get('not_collected') ==
                'Optional discovery RPCs disabled for this profile' for d in discovery)
        ordering_design = 'Single-client interface follow-up; separate condition and time window'
    for name, sha in environment['harness_sha256'].items():
        assert hashlib.sha256((path / 'harness' / name).read_bytes()).hexdigest() == sha
    for t in trials:
        assert hashlib.sha256((path / t['settings']['file']).read_bytes()).hexdigest() == t['settings']['sha256']
    observations = [json.loads(line) for line in (path / 'host-link.jsonl').read_text().splitlines()]
    assert observations and all(o['ok'] for o in observations), 'Ethernet route/link anomaly; inspect observations'
    times = [timestamp(o['utc']) for o in observations]
    assert times[0] <= min(timestamp(t['utc_start']) for t in trials)
    assert times[-1] >= max(timestamp(t['utc_end']) for t in trials)
    gaps = [(b - a).total_seconds() for a, b in zip(times, times[1:])]
    assert gaps and min(gaps) >= 0 and max(gaps) <= 30, 'Host monitor coverage gap'
    sample_path = path / 'samples.jsonl.gz'
    opener = gzip.open
    if not sample_path.exists():
        sample_path, opener = path / 'samples.jsonl', open
    with opener(sample_path, 'rt') as handle:
        cadence = audit_samples(trials, (json.loads(line) for line in handle))
    validation.update({
        'registered_orders_matched': True, 'ordering_design': ordering_design,
        'balanced_positions': len(positions),
        'balanced_within_round_directed_pairs': len(transitions),
        'archived_harness_files_verified': len(environment['harness_sha256']),
        'per_trial_settings_verified': len(trials), 'dual_stack_network': True,
        'host_link_observations': len(observations), 'host_link_all_ok': True,
        'max_host_observation_gap_s': max(gaps),
        'resource_aggregates_recomputed': len(trials),
        'no_optional_diagnostic_rpc_errors': True,
        'max_resource_sample_gap_s': max(stats['max'] for stats in cadence.values()),
        'sampling_interval_s_by_client': cadence,
        'experiment_utc_start': trials[0]['utc_start'],
        'experiment_utc_end': trials[-1]['utc_end'],
        'analysis_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    inputs = ['protocol.json', 'environment.json', 'host-link.jsonl']
    for name in ('observations.json', 'followup-plan.json', 'followup-decision.json', 'study.json'):
        if (path / name).exists():
            inputs.append(name)
    for name in inputs:
        validation['input_sha256'][name] = hashlib.sha256((path / name).read_bytes()).hexdigest()
    return validation


def number(value, digits=2):
    return '—' if value is None else f'{value:,.{digits}f}'


def summary_markdown(rows, validation, trials):
    lines = ['# Repeated public Ubuntu fresh-download experiment', '',
             f'Six registered attempts per client, {len(trials)} total; a fixed 900-second deadline, '
             'without an early stall cutoff. Median, interquartile range (IQR), and full '
             'range describe completed, SHA-256 verified downloads. Every failure remains '
             'in the completion count and receives 900 seconds in the penalized mean. '
             'Inclusive quartiles use linear interpolation at rank (n−1)×p. '
             'Speed and duration medians are computed separately from per-attempt values.', '',
             '| Client | Completed | Wilson 95% completion interval | Median MiB/s | IQR MiB/s | Range MiB/s | Median seconds | Mean penalized seconds |',
             '|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        speed = r['mib_s']
        lines.append('| ' + ' | '.join([
            r['client'], f'{r["completed"]}/{r["n"]}',
            '–'.join(f'{v * 100:.1f}%' for v in r['completion_wilson95']),
            number(speed['median']), number(speed['q1']) + '–' + number(speed['q3']),
            number(speed['min']) + '–' + number(speed['max']),
            number(r['elapsed_s']['median']), number(r['deadline_penalized_mean_s'])]) + ' |')
    lines += ['', '**All-attempt resource costs, including failed/partial work.** Memory cells show the median '
              'of per-attempt sampled peaks / the largest sampled peak. Charged memory '
              'includes filesystem cache; RSS includes resident mappings; anonymous '
              'memory isolates resident allocations. These are different counters.', '',
              '| Client | CPU core-s median (range) | Peak anonymous MiB, median / max | Peak RSS MiB, median / max | Peak charged MiB, median / max | Peak working MiB, median / max |',
              '|---|---:|---:|---:|---:|---:|']
    for r in rows:
        cpu = r['cpu_s']
        values = [r['client'], number(cpu['median']) + ' (' + number(cpu['min']) + '–' + number(cpu['max']) + ')']
        values += [number(r[f]['median']) + ' / ' + number(r[f]['max'])
                   for f in ('peak_anon_mib', 'peak_rss_mib', 'peak_memory_mib', 'peak_working_mib')]
        lines.append('| ' + ' | '.join(values) + ' |')
    lines += ['', '**Completed-download resource costs.** The following subset excludes failed '
              'attempts, whose resources may cover discovery or only a small part of the ISO. '
              'Use this subset for loaded-download comparisons. '
              'Cells again show median / maximum sampled peak; CPU is a median.', '',
              '| Client | Verified downloads | CPU core-s | Peak anonymous MiB | Peak RSS MiB | Peak charged MiB | Peak working MiB |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        costs = r['completed_resources']
        values = [r['client'], str(r['completed']), number(costs['cpu_s']['median'])]
        values += [number(costs[f]['median']) + ' / ' + number(costs[f]['max'])
                   for f in ('peak_anon_mib', 'peak_rss_mib', 'peak_memory_mib', 'peak_working_mib')]
        lines.append('| ' + ' | '.join(values) + ' |')
    lines += ['', '**Discovery and observation quality.** Startup/active rates are omitted '
              'for rqbit and rTorrent because their counters can include initialization '
              'or hash-scan work. A dash also denotes unavailable address-family counters '
              '(not captured for rqbit). Peer maxima are sampled address counts from native APIs, with '
              'different client semantics, not unique-peer totals or a normalized capacity measure. '
              'Sampling intervals are median / maximum seconds; '
              'resource peaks can miss brief spikes, especially during the longer gaps.', '',
              '| Client | First payload s (valid n) | Active 10–90% MiB/s (valid n) | Max observed IPv4 peers | Max observed IPv6 peers | Resource interval s | Status interval s |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        values = [r['client']]
        for field in ('first_observed_payload_s', 'active_10_90_mib_s'):
            values.append(number(r[field]['median']) + f' ({r[field]["n"]})')
        values += [number(r['discovery'][f'max_observed_ipv{family}_peers'], 0) for family in (4, 6)]
        values += [number(r[field]['median'], 3) + ' / ' + number(r[field]['max'], 3)
                   for field in ('sampling_interval_s', 'status_poll_interval_s')]
        lines.append('| ' + ' | '.join(values) + ' |')
    lines += ['', '**Every registered attempt, in execution order.** Network receive bytes '
              'include BitTorrent and control/protocol traffic. The complete-file rate '
              'is absent on failure. CPU and sampled memory peaks describe that attempt; '
              'the sample count makes uneven resource observation visible.', '',
              '| Slot | Round | Client | Result | Seconds | MiB/s | Received MiB | CPU core-s | Peak anonymous MiB | Peak RSS MiB | Peak charged MiB | Samples |',
              '|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for slot, t in enumerate(trials, 1):
        m = t['metrics']['client']
        values = [str(slot), str(t['repeat'] + 1), t['client'], t['status'], number(t['elapsed_s']),
                  number(t['mib_s']), number(m['network_rx'] / 1024 ** 2), number(m['cpu_s'])]
        values += [number(m[f]) for f in ('peak_anon_mib', 'peak_rss_mib', 'peak_memory_mib')]
        values.append(str(t['metrics']['samples']))
        lines.append('| ' + ' | '.join(values) + ' |')
    lines += ['', f"Audit: {validation['trials']} attempts; {validation['independent_sha256_checks']} independent SHA-256 checks; "
              f"{validation['resource_samples']:,} resource samples; {validation['host_link_observations']} "
              'sanitized Ethernet/route observations. No ISO retained.', '',
              'This experiment describes cold client state on this host, network, and swarm '
              'during the recorded window. It does not estimate universal client capacity. '
              'Six trials still have substantial uncertainty; even 6/6 completions gives '
              'a Wilson lower bound of about 61%, under a binomial model. Swarm and temporal '
              'dependence further limit that model. There are no significance claims.', '']
    return '\n'.join(lines)


def analyze(path):
    trials = json.loads((path / 'trials.json').read_text())
    environment = json.loads((path / 'environment.json').read_text())
    source = json.loads((path / 'torrent-source.json').read_text())
    validation = audit_registered(path, trials, environment, source)
    deadline = environment['arguments']['timeout']
    rows = [summarize_client([t for t in trials if t['client'] == client], deadline)
            for client in environment['arguments']['clients']]
    for row in rows:
        row['sampling_interval_s'] = validation['sampling_interval_s_by_client'][row['client']]
    write_json = lambda name, obj: (path / name).write_text(json.dumps(obj, indent=2) + '\n')
    write_json('validation.json', validation)
    write_json('analysis.json', {'deadline_s': deadline, 'quartiles': 'inclusive', 'clients': rows})
    flat = []
    for row in rows:
        item = {k: row[k] for k in ('client', 'n', 'completed', 'deadline_penalized_mean_s')}
        item.update({f'completion_wilson95_{side}': value
                     for side, value in zip(('low', 'high'), row['completion_wilson95'])})
        for key, value in row.items():
            if isinstance(value, dict) and 'median' in value:
                item.update({f'{key}_{stat}': v for stat, v in value.items()})
        for key, value in row['completed_resources'].items():
            item.update({f'completed_{key}_{stat}': v for stat, v in value.items()})
        flat.append(item)
    with (path / 'summary.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat[0]))
        writer.writeheader()
        writer.writerows(flat)
    attempts = []
    for slot, t in enumerate(trials, 1):
        attempts.append({'slot': slot, 'round': t['repeat'] + 1, 'client': t['client'],
                         'status': t['status'], 'elapsed_s': t['elapsed_s'], 'mib_s': t['mib_s'],
                         'resource_samples': t['metrics']['samples'],
                         'mean_resource_sample_gap_s': t['metrics']['measurement_s'] / (t['metrics']['samples'] - 1),
                         **{k: t['metrics']['client'][k] for k in ('cpu_s', 'peak_anon_mib',
                             'peak_rss_mib', 'peak_memory_mib', 'network_rx', 'network_tx')}})
    with (path / 'attempts.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(attempts[0]))
        writer.writeheader()
        writer.writerows(attempts)
    (path / 'SUMMARY.md').write_text(summary_markdown(rows, validation, trials))
    print(json.dumps(validation, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    analyze(parser.parse_args().directory)
