"""Fresh public Ubuntu downloads; one shared payload, deleted after every trial."""
import argparse
import datetime
import hashlib
import json
import random
import shutil
import time
import traceback
from pathlib import Path

from api import CLIENTS, docker
from fixtures import MIB, ROOT
from run import Benchmark, TrialFailure, TransferTimeout, transfer_details, verify, write_json
from public_diagnostics import diagnostics

PROJECT = 'torrent-bench-ubuntu'
SCRATCH = Path('/clients/qbittorrent/data')


def balanced_orders(clients, repeats, seed):
    """Williams order: six rounds balance positions and within-round carryover."""
    rng = random.Random(seed)
    labels = list(clients)
    rng.shuffle(labels)
    n = len(labels)
    pattern = [0]
    for step in range(1, n):
        pattern.append((step + 1) // 2 if step % 2 else n - step // 2)
    starts = list(range(n))
    rng.shuffle(starts)
    return [[labels[(start + offset) % n] for offset in pattern]
            for start in (starts * ((repeats + n - 1) // n))[:repeats]]


def clear_payload(path=SCRATCH):
    count = 0
    for child in path.iterdir():
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()
        count += 1
    assert not list(path.iterdir())
    return {'removed_entries': count, 'remaining_entries': 0, 'iso_retained': False}


class UbuntuBenchmark(Benchmark):
    def __init__(self, args):
        super().__init__(args, project=PROJECT, reference_peers=False)
        assert len(self.fixtures) == 1
        self.torrent = self.fixtures[0]
        source = json.loads((ROOT / 'source.json').read_text())
        metadata = (ROOT / 'torrents/ubuntu.torrent').read_bytes()
        assert hashlib.sha256(metadata).hexdigest() == source['torrent_sha256']
        assert self.torrent['hash'] == source['info_hash']
        assert self.torrent['bytes'] == source['payload_bytes']
        assert self.torrent['files'][0]['sha256'] == source['iso_sha256']
        internet = docker('GET', '/networks/' + PROJECT + '_internet')
        assert not internet['Internal']
        assert internet['EnableIPv6'], 'The registered public experiment requires dual-stack networking'
        for name in CLIENTS:
            data = docker('GET', '/containers/' + self.ids[name] + '/json')
            assert not data['HostConfig'].get('PortBindings')
            mount = next(m for m in data['Mounts'] if m['Destination'] == '/downloads')
            assert mount['Name'] == PROJECT + '_scratch'
            assert set(data['NetworkSettings']['Networks']) == {PROJECT + '_lab', PROJECT + '_internet'}
        self.environment.update(mode='public Ubuntu swarm',
            public_network={'name': PROJECT + '_internet', 'internal': False, 'ipv6': True},
            host_link={'interface': args.host_interface, 'link': args.host_link},
            payload_retention='Deleted after every trial; shared scratch volume removed on exit.',
            discovery='DHT and PEX enabled; LAN discovery and port forwarding disabled.',
            transport='Native IPv4/IPv6 and TCP/uTP support; no published incoming ports.')
        self.orders = balanced_orders(args.clients, args.repeats, args.order_seed)
        self.protocol = {'schema': 2, 'registered_utc': self.environment['utc'],
            'repeats': args.repeats, 'orders': self.orders, 'order_seed': args.order_seed,
            'deadline_s': args.timeout, 'early_no_progress_cutoff_s': args.stall_seconds or None,
            'timer': 'API submission through client completion; daemon startup excluded',
            'state': 'Fresh daemon, configuration, DHT routing table, and destination for every attempt',
            'network': 'Dual-stack outgoing Docker network; no forwarded incoming ports',
            'limits': {'cpu_cores': 2, 'charged_memory_mib': 1536, 'swap': False},
            'primary_outcomes': ['Completion within deadline, including all assigned attempts',
                'Completion time and complete-file MiB/s, conditional on verified completion'],
            'secondary_outcomes': ['First payload and 10-90% rate where progress is unambiguous',
                'CPU core-seconds, sampled RSS/anonymous/charged/working memory peaks',
                'Payload progress on failure, network receive/transmit bytes'],
            'analysis': 'Per-attempt points, median, IQR, range; completion Wilson 95% interval; '
                        'deadline-penalized completion time includes failures; no fastest-run selection',
            'stopping_rule': 'Execute every registered slot once. Retain errors/timeouts; '
                             'do not replace slow or failed valid attempts.',
            'environment_exclusions': 'Any observed Ethernet outage/route change or instrumentation '
                                     'failure invalidates affected measurements; retain evidence and disclose reruns.',
            'payload_retention': 'Independent SHA-256 verification, then delete ISO/sidecars before next slot'}
        write_json(self.output / 'environment.json', self.environment)
        write_json(self.output / 'torrent-source.json', source)
        write_json(self.output / 'protocol.json', self.protocol)
        archive = self.output / 'harness'
        archive.mkdir()
        for path in Path('/bench').glob('*.py'):
            shutil.copyfile(path, archive / path.name)

    def preflight(self):
        """Check every adapter with a paused torrent before registering timed runs."""
        checks = []
        for name in CLIENTS:
            self.stop(name)
        try:
            for name in self.args.clients:
                client = self.start(name, public=True)
                try:
                    client.add(self.torrent, paused=True)
                    deadline = time.monotonic() + 15
                    while not client.status():
                        if time.monotonic() > deadline:
                            raise TimeoutError('Paused metadata was not registered: ' + name)
                        time.sleep(0.2)
                    checks.append({'client': name, 'version': client.ready(),
                                   'diagnostics': diagnostics(client, name, self.torrent)})
                finally:
                    self.stop(name)
                    clear_payload()
            write_json(self.output / 'preflight.json', {'ok': True, 'checks': checks})
        finally:
            for name in CLIENTS:
                self.stop(name)
            clear_payload()

    def transfer(self, client, name, repeat):
        start = last_progress = time.monotonic()
        samples = []
        discovery = []
        last_diagnostic = -15
        previous_bytes, last_log = -1, -1
        client.add(self.torrent)
        while True:
            rows = [r for r in client.status() if r['id'] == self.torrent['hash']]
            now = time.monotonic()
            done_bytes = sum(row['bytes'] for row in rows)
            samples.append((now - start, done_bytes))
            if now - start - last_diagnostic >= 15:
                try:
                    counters = diagnostics(client, name, self.torrent)
                except Exception as error:
                    counters = {'diagnostic_error_type': type(error).__name__}
                discovery.append({'seconds': now - start, **counters})
                last_diagnostic = now - start
            # A tracker warning is recoverable while other trackers/DHT still work.
            if any(row['error'] and not (name == 'rtorrent' and
                   str(row['state']).startswith('Tracker:')) for row in rows):
                raise TrialFailure({**transfer_details(samples, self.torrent['bytes']),
                    'reason': 'Client reported a torrent error', 'discovery': discovery,
                    'verified_payload_bytes': done_bytes,
                    'states': [{k: r[k] for k in ('done', 'bytes', 'checking', 'paused', 'error')}
                               for r in rows]})
            if done_bytes > previous_bytes:
                last_progress, previous_bytes = now, done_bytes
            if rows and all(row['done'] and not row['checking'] for row in rows):
                return {**transfer_details(samples, self.torrent['bytes']), 'discovery': discovery,
                        'completed_torrents': 1,
                        'final_states': {str(rows[0]['state']): 1}}
            if now - start > self.args.timeout or (self.args.stall_seconds and
                                                   now - last_progress > self.args.stall_seconds):
                raise TransferTimeout({**transfer_details(samples, self.torrent['bytes']),
                    'discovery': discovery,
                    'reason': 'Download deadline or no-progress limit reached',
                    'verified_payload_bytes': done_bytes})
            log = int((now - start) // 30)
            if log != last_log:
                print(json.dumps({'event': 'progress', 'client': name, 'repeat': repeat,
                    'seconds': round(now - start, 1), 'completed_mib': round(done_bytes / MIB, 1),
                    'discovery': discovery[-1] if discovery else {}}), flush=True)
                last_log = log
            time.sleep(0.2)

    def trial(self, name, repeat):
        trial = None
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        try:
            client = self.start(name, public=True)
            settings_path = Path('settings') / f'{name}-{repeat}.json'
            (self.output / 'settings').mkdir(exist_ok=True)
            shutil.copyfile(self.output / (name + '-effective-settings.json'), self.output / settings_path)
            trial = self.measured(name, repeat, 'ubuntu-public',
                lambda: self.transfer(client, name, repeat), self.torrent['bytes'])
            trial['settings'] = {'file': str(settings_path), 'sha256':
                hashlib.sha256((self.output / settings_path).read_bytes()).hexdigest()}
            trial['utc_start'] = started
            # End public seeding before the independent verification pass.
            self.stop(name)
            if trial['status'] == 'ok':
                trial['verification'] = verify([self.torrent], name)
                assert trial['metrics']['client']['network_rx'] >= self.torrent['bytes']
        finally:
            try:
                self.stop(name)
            finally:
                cleanup = clear_payload()
                if trial is not None:
                    trial['cleanup'] = cleanup
                    trial['utc_end'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                    write_json(self.output / 'trials.json', self.results)

    def run(self):
        for name in CLIENTS:
            self.stop(name)
        clear_payload()
        try:
            for repeat, order in enumerate(self.orders):
                for name in order:
                    assert not list(SCRATCH.iterdir())
                    self.trial(name, repeat)
            write_json(self.output / 'complete.json', {'ok': True, 'trials': len(self.results),
                'timeouts': [{k: row[k] for k in ('client', 'repeat', 'workload')}
                             for row in self.results if row['status'] != 'ok'],
                'scratch_empty': not list(SCRATCH.iterdir())})
        except BaseException:
            (self.output / 'failure.txt').write_text(traceback.format_exc())
            raise
        finally:
            for name in CLIENTS:
                self.stop(name)
            clear_payload()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--repeats', type=int, default=6)
    parser.add_argument('--clients', nargs='+', choices=list(CLIENTS), default=list(CLIENTS))
    parser.add_argument('--timeout', type=float, default=900)
    parser.add_argument('--stall-seconds', type=float, default=0)
    parser.add_argument('--order-seed', type=int, default=20261103)
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--host-interface', default='not recorded')
    parser.add_argument('--host-link', default='not recorded')
    parser.add_argument('--output', default='ubuntu-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
    args = parser.parse_args()
    benchmark = UbuntuBenchmark(args)
    benchmark.preflight() if args.preflight else benchmark.run()
