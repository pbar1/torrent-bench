"""Run isolated, serial trials; retain raw metrics and independently verify bytes."""
import argparse
import concurrent.futures
import datetime
import hashlib
import json
import os
import shutil
import statistics
import threading
import time
import traceback
from pathlib import Path

from api import CLIENTS, HTTP, containers, docker
from fixtures import MIB, ROOT


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def transfer_details(samples, total):
    # Some APIs report initialization/hash-check progress in the same byte field.
    # A reset makes intermediate transfer-rate/startup estimates ambiguous.
    monotonic = all(b >= previous for (_, previous), (_, b) in zip(samples, samples[1:]))
    low = next(((t, b) for t, b in samples if b >= total * 0.1), None)
    high = next(((t, b) for t, b in samples if b >= total * 0.9), None)
    rate = ((high[1] - low[1]) / MIB / (high[0] - low[0])
            if low and high and high[0] > low[0] else None)
    return {'first_observed_payload_s': next((t for t, b in samples if b), None) if monotonic else None,
            'active_10_90_mib_s': rate if monotonic else None,
            'progress_monotonic': monotonic,
            'progress_samples': [[round(t, 4), b] for t, b in samples]}


class TrialFailure(Exception):
    def __init__(self, details, status='error'):
        self.details, self.status = details, status


class TransferTimeout(TrialFailure):
    def __init__(self, details):
        super().__init__(details, 'timeout')


def reset(name, public=False):
    base = Path('/clients') / name
    for folder in ('config', 'data'):
        path = base / folder
        for child in path.iterdir():
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()
        os.chown(path, 1000, 1000)
    config = base / 'config'
    if name == 'qbittorrent':
        (config / 'qBittorrent/config').mkdir(parents=True)
        (config / 'qBittorrent/config/qBittorrent.conf').write_text(
            '[LegalNotice]\nAccepted=true\n[WebUI]\n'
            'AuthSubnetWhitelist=0.0.0.0/0\n'
            'AuthSubnetWhitelistEnabled=true\n'
            'CSRFProtection=false\nHostHeaderValidation=false\n'
            '[BitTorrent]\nSession\\DHTEnabled=false\nSession\\LSDEnabled=false\n'
            'Session\\PeXEnabled=false\nSession\\DefaultSavePath=/downloads\n')
    elif name == 'deluge':
        # Deluge config files contain a version header followed by JSON.
        (config / 'core.conf').write_text(json.dumps({'file': 1, 'format': 1}) + '\n' + json.dumps({
            'download_location': '/downloads', 'dht': False, 'lsd': False, 'utpex': False,
            'upnp': False, 'natpmp': False, 'listen_ports': [6881, 6881], 'random_port': False}))
    elif name == 'transmission':
        write_json(config / 'settings.json', {
            'rpc-bind-address': '0.0.0.0', 'rpc-whitelist-enabled': False,
            'rpc-host-whitelist-enabled': False, 'rpc-authentication-required': False,
            'download-dir': '/downloads', 'dht-enabled': False, 'pex-enabled': False,
            'lpd-enabled': False, 'port-forwarding-enabled': False, 'peer-port': 6881,
            'peer-port-random-on-start': False})
    elif name == 'rtorrent':
        (config / 'session').mkdir()
        (config / 'rtorrent.rc').write_text('''system.daemon.set = true
network.scgi.open_port = 0.0.0.0:5000
network.listen.port.range.set = 6881-6881
network.listen.port.random.set = no
directory.default.set = /downloads
session.path.set = /config/session
dht.mode.set = disable
protocol.pex.set = no
trackers.use_udp.set = no
throttle.max_peers.normal.set = 100
throttle.max_peers.seed.set = 100
throttle.max_uploads.set = 100
''')
    for path in config.rglob('*'):
        os.chown(path, 1000, 1000)
    if public and name == 'rtorrent':
        path = config / 'rtorrent.rc'
        path.write_text(path.read_text().replace('dht.mode.set = disable', 'dht.mode.set = on')
                        .replace('protocol.pex.set = no', 'protocol.pex.set = yes')
                        .replace('trackers.use_udp.set = no', 'trackers.use_udp.set = yes'))
        with path.open('a') as handle:
            handle.write('''dht.port.set = 6881
dht.add_node = dht.transmissionbt.com:6881
dht.add_node = router.bittorrent.com:6881
dht.add_node = router.bitcomet.com:6881
''')


def wait_ready(client, timeout=90, cid=None):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        try:
            return client.ready()
        except Exception as e:
            last = e
            if cid and not docker('GET', '/containers/' + cid + '/json')['State']['Running']:
                logs = docker('GET', '/containers/' + cid + '/logs?stdout=true&stderr=true&tail=30', raw=True)
                raise RuntimeError(f'Client exited during startup: {logs!r}') from e
            time.sleep(0.5)
    raise RuntimeError(f'Client not ready: {last}')


def peer_control(names, mode='seed', rate=0):
    def configure(i):
        host = ('leech' if mode == 'leech' else 'peer') + str(i)
        return HTTP(f'http://{host}:8080').call('/', value={
            'mode': mode, 'names': names, 'rate': rate})
    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        return list(pool.map(configure, (1, 2)))


def verify_once(torrents, name):
    count = size = 0
    for torrent in torrents:
        for file in torrent['files']:
            path = Path('/clients') / name / 'data' / file['path']
            digest = hashlib.sha256()
            with path.open('rb') as f:
                while chunk := f.read(4 * MIB):
                    digest.update(chunk)
            if path.stat().st_size != file['bytes'] or digest.hexdigest() != file['sha256']:
                raise AssertionError(f'Independent SHA-256 verification failed: {path}')
            size += file['bytes']
            count += 1
    return {'files': count, 'bytes': size, 'sha256': 'all matched'}


def verify(torrents, name):
    start = time.monotonic()
    attempts = 0
    first_error = None
    while True:
        attempts += 1
        try:
            result = verify_once(torrents, name)
            return {**result, 'attempts': attempts, 'seconds': time.monotonic() - start,
                    'initial_error': first_error}
        except (AssertionError, FileNotFoundError) as error:
            # A completed piece can still have a queued disk write or rename.
            # Keep the discrepancy visible and require correct filesystem bytes.
            first_error = first_error or str(error)
            if time.monotonic() - start >= 30:
                raise
            time.sleep(0.25)


def snapshot(cid):
    s = docker('GET', f'/containers/{cid}/stats?stream=false&one-shot=true')
    mem = s['memory_stats']
    stat = mem.get('stats', {})
    cpu = s['cpu_stats']
    # Aggregate process RSS complements cgroup accounting: shared executable pages
    # may be charged to a different cgroup, and file mappings matter for mmap clients.
    top = docker('GET', f'/containers/{cid}/top?ps_args=-eo%20pid,rss,comm')
    rss_mib = sum(int(row[1]) for row in top['Processes']) / 1024
    return {'cpu_s': cpu['cpu_usage']['total_usage'] / 1e9,
            'rss_mib': rss_mib,
            'memory_mib': mem.get('usage', 0) / MIB,
            'working_mib': max(0, mem.get('usage', 0) - stat.get('inactive_file', 0)) / MIB,
            'anon_mib': stat.get('anon', stat.get('rss', 0)) / MIB,
            'file_mib': stat.get('file', stat.get('cache', 0)) / MIB,
            'throttled_s': cpu.get('throttling_data', {}).get('throttled_time', 0) / 1e9,
            'network_rx': sum(x['rx_bytes'] for x in s.get('networks', {}).values()),
            'network_tx': sum(x['tx_bytes'] for x in s.get('networks', {}).values()),
            'io_read': sum(x['value'] for x in s.get('blkio_stats', {}).get('io_service_bytes_recursive', []) or []
                           if x['op'].lower() == 'read'),
            'io_write': sum(x['value'] for x in s.get('blkio_stats', {}).get('io_service_bytes_recursive', []) or []
                            if x['op'].lower() == 'write')}


class Meter:
    def __init__(self, ids, client, output, reference_peers=True):
        self.ids, self.client, self.output = ids, client, output
        self.labels = ('client', 'peer1', 'peer2') if reference_peers else ('client',)
        self.samples = []
        self.stop_event = threading.Event()

    def collect(self):
        ids = [self.ids[self.client]] + [self.ids[p] for p in self.labels[1:]]
        with concurrent.futures.ThreadPoolExecutor(len(ids)) as pool:
            values = list(pool.map(snapshot, ids))
        sample = {'time': time.monotonic(), **dict(zip(self.labels, values))}
        self.samples.append(sample)

    def loop(self):
        while not self.stop_event.wait(0.5):
            try:
                self.collect()
            except Exception as e:
                self.samples.append({'time': time.monotonic(), 'error': str(e)})

    def start(self):
        self.collect()
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()

    def finish(self, tag):
        self.stop_event.set()
        self.thread.join()
        self.collect()
        with (self.output / 'samples.jsonl').open('a') as f:
            for sample in self.samples:
                f.write(json.dumps({'trial': tag, **sample}) + '\n')
        valid = [s for s in self.samples if 'error' not in s]
        if len(valid) != len(self.samples):
            raise RuntimeError('Metric sampling failed; see samples.jsonl')
        first, last = valid[0], valid[-1]
        elapsed = last['time'] - first['time']
        metrics = {'samples': len(valid), 'measurement_s': elapsed}
        for key in self.labels:
            rows = [s[key] for s in valid]
            metrics[key] = {f'peak_{field}': max(r[field] for r in rows)
                            for field in ('memory_mib', 'working_mib', 'anon_mib', 'file_mib', 'rss_mib')}
            metrics[key].update({f'median_{field}': statistics.median(r[field] for r in rows)
                                for field in ('memory_mib', 'working_mib', 'anon_mib', 'file_mib', 'rss_mib')})
            for field in ('cpu_s', 'throttled_s', 'network_rx', 'network_tx', 'io_read', 'io_write'):
                metrics[key][field] = last[key][field] - first[key][field]
            metrics[key]['cpu_pct_one_core'] = metrics[key]['cpu_s'] / elapsed * 100
        return metrics


class Benchmark:
    def __init__(self, args, project='torrent-bench', reference_peers=True):
        self.args = args
        self.ids = containers(project)
        self.reference_peers = reference_peers
        self.fixtures = json.loads((ROOT / 'manifest.json').read_text())
        self.output = Path('/results') / args.output
        self.output.mkdir(parents=True, exist_ok=True)
        if (self.output / 'trials.json').exists():
            raise RuntimeError('Choose a fresh --output; previous results are never overwritten')
        self.results = []
        info = docker('GET', '/info')
        self.environment = {k: info[k] for k in (
            'NCPU', 'MemTotal', 'KernelVersion', 'OperatingSystem', 'Architecture',
            'ServerVersion', 'Driver', 'CgroupVersion')}
        self.environment['utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.environment['arguments'] = vars(args)
        self.environment['harness_sha256'] = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/bench').glob('*.py')}
        network_name = project + '_lab'
        network = docker('GET', '/networks/' + network_name)
        if not network['Internal']:
            raise RuntimeError('The benchmark network must be internal')
        self.environment['network'] = {'name': network_name, 'internal': network['Internal'],
                                       'ipam': network['IPAM']}
        shutil.copyfile(ROOT / 'manifest.json', self.output / 'fixtures-manifest.json')
        self.environment['containers'] = {}
        names = list(CLIENTS) + (['peer1', 'peer2', 'leech1', 'leech2'] if reference_peers else [])
        for name in names:
            inspect = docker('GET', '/containers/' + self.ids[name] + '/json')
            image = docker('GET', '/images/' + inspect['Image'] + '/json')
            self.environment['containers'][name] = {
                'image_id': inspect['Image'], 'image_ref': inspect['Config']['Image'],
                'image_digests': image.get('RepoDigests'), 'architecture': image['Architecture'],
                'host_config': {k: inspect['HostConfig'][k] for k in (
                    'NanoCpus', 'Memory', 'MemorySwap', 'NetworkMode')},
                'command': inspect['Config']['Cmd']}
        write_json(self.output / 'environment.json', self.environment)

    def stop(self, name):
        docker('POST', '/containers/' + self.ids[name] + '/stop?t=10')
        inspect = docker('GET', '/containers/' + self.ids[name] + '/json')
        if inspect['State']['OOMKilled']:
            raise RuntimeError(name + ' was OOM killed')

    def start(self, name, public=False):
        reset(name, public=public)
        docker('POST', '/containers/' + self.ids[name] + '/start')
        client = CLIENTS[name]()
        wait_ready(client, cid=self.ids[name])
        config = client.configure(public=public)
        if name == 'rtorrent':
            config['configuration'] = (Path('/clients') / name / 'config/rtorrent.rc').read_text()
        write_json(self.output / (name + '-effective-settings.json'), config)
        return client

    def measured(self, name, repeat, workload, action, byte_count=0):
        tag = {'client': name, 'repeat': repeat, 'workload': workload}
        print(json.dumps({'event': 'start', **tag}), flush=True)
        metric_ids = dict(self.ids)
        if workload == 'upload-2-peers':
            metric_ids.update(peer1=self.ids['leech1'], peer2=self.ids['leech2'])
        meter = Meter(metric_ids, name, self.output, reference_peers=self.reference_peers)
        meter.start()
        start = time.monotonic()
        status = 'ok'
        try:
            details = action()
        except TrialFailure as error:
            details = error.details
            status = error.status
        except BaseException:
            meter.finish(tag)
            raise
        duration = time.monotonic() - start
        metrics = meter.finish(tag)
        result = {**tag, 'status': status, 'elapsed_s': duration, 'payload_bytes': byte_count,
                  'mib_s': byte_count / MIB / duration if byte_count and status == 'ok' else None,
                  'metrics': metrics, 'details': details}
        self.results.append(result)
        write_json(self.output / 'trials.json', self.results)
        print(json.dumps({'event': 'finished', **tag, 'seconds': round(duration, 3),
                          'status': status, 'mib_s': round(result['mib_s'], 2) if result['mib_s'] else None,
                          'peak_anon_mib': round(metrics['client']['peak_anon_mib'], 1)}), flush=True)
        return result

    def complete(self, client, torrents, timeout=600, start=None):
        expected = {t['hash'] for t in torrents}
        deadline = time.monotonic() + timeout
        start = time.monotonic() if start is None else start
        samples = []
        while time.monotonic() < deadline:
            rows = [t for t in client.status() if t['id'] in expected]
            if any(t['error'] for t in rows):
                raise RuntimeError(f'Torrent error: {rows[:5]}')
            samples.append((time.monotonic() - start, sum(t['bytes'] for t in rows)))
            if len(rows) == len(torrents) and all(t['done'] and not t['checking'] for t in rows):
                return {**transfer_details(samples, sum(t['bytes'] for t in torrents)),
                        'completed_torrents': len(rows),
                        'final_states': {str(s): sum(t['state'] == s for t in rows)
                                         for s in {t['state'] for t in rows}}}
            time.sleep(0.2)
        raise TimeoutError(f'Download timed out: {rows[:5]}')

    def download(self, name, repeat, group):
        torrents = [t for t in self.fixtures if t['group'] == group]
        peer_control([t['name'] for t in torrents], rate=16 * MIB if group == 'shaped' else 0)
        client = self.start(name)
        try:
            if group == 'large':
                self.measured(name, repeat, 'idle-empty', lambda: time.sleep(self.args.idle_seconds))

            def transfer():
                start = time.monotonic()
                for torrent in torrents:
                    client.add(torrent)
                return self.complete(client, torrents, start=start)

            trial = self.measured(name, repeat, 'download-' + group, transfer,
                                  sum(t['bytes'] for t in torrents))
            # Hash the resulting bytes independently, outside the timed transfer.
            trial['verification'] = verify(torrents, name)
            write_json(self.output / 'trials.json', self.results)
            if group == 'concurrent':
                self.measured(name, repeat, 'idle-64-seeds', lambda: time.sleep(self.args.idle_seconds))
            if group == 'large':
                peer_control([])
                torrent = torrents[0]

                def recheck():
                    client.recheck(torrent)
                    saw_checking = False
                    deadline = time.monotonic() + 180
                    while time.monotonic() < deadline:
                        states = client.status()
                        saw_checking |= any(t['checking'] for t in states)
                        if states and all(t['done'] and not t['checking'] for t in states):
                            if saw_checking:
                                return {'observed_checking': True}
                        time.sleep(0.05)
                    raise TimeoutError('Recheck did not finish')

                self.measured(name, repeat, 'recheck-large', recheck, torrent['bytes'])
                # Use real independent libtorrent leechers, not /dev/null readers.
                def upload():
                    start = time.monotonic()
                    samples = []
                    last_progress, last_bytes = start, -1
                    peer_control([torrent['name']], mode='leech')
                    deadline = time.monotonic() + 600
                    while time.monotonic() < deadline:
                        rows = [HTTP(f'http://leech{i}:8080').call('/') for i in (1, 2)]
                        if any(row['errors'] for row in rows):
                            raise RuntimeError(rows)
                        if any(row['uploaded'] for row in rows):
                            raise AssertionError('Reference leechers uploaded data; upload trial is invalid')
                        now = time.monotonic()
                        transferred = sum(row['bytes'] for row in rows)
                        samples.append((now - start, transferred))
                        if transferred > last_bytes:
                            last_progress, last_bytes = now, transferred
                        if all(row['done'] == 1 for row in rows):
                            if any(row['downloaded'] < torrent['bytes'] for row in rows):
                                raise AssertionError('A leecher completed without receiving the full payload')
                            return {'leechers': rows,
                                    **transfer_details(samples, 2 * torrent['bytes'])}
                        if now - last_progress > 120:
                            raise TransferTimeout({'reason': 'No verified payload progress for 120 seconds',
                                                  'verified_payload_bytes': transferred, 'leechers': rows,
                                                  **transfer_details(samples, 2 * torrent['bytes'])})
                        time.sleep(0.2)
                    raise TransferTimeout({'reason': 'Upload exceeded 600 seconds', 'leechers': rows,
                                          'verified_payload_bytes': sum(row['bytes'] for row in rows),
                                          **transfer_details(samples, 2 * torrent['bytes'])})

                self.measured(name, repeat, 'upload-2-peers', upload, 2 * torrent['bytes'])
        finally:
            self.stop(name)
            peer_control([])
            peer_control([], mode='leech')

    def catalog(self, name, repeat):
        torrents = [t for t in self.fixtures if t['group'] == 'catalog']
        client = self.start(name)
        try:
            def add():
                for torrent in torrents:
                    client.add(torrent, paused=True)
                deadline = time.monotonic() + 180
                while time.monotonic() < deadline:
                    statuses = client.status()
                    if len(statuses) == len(torrents) and not any(t['checking'] for t in statuses):
                        if not all(t['paused'] for t in statuses):
                            raise AssertionError('The catalog must contain only paused torrents')
                        return {'registered_torrents': len(torrents),
                                'states': dict((str(s), sum(t['state'] == s for t in statuses))
                                               for s in {t['state'] for t in statuses})}
                    time.sleep(0.5)
                raise TimeoutError('Catalog not fully registered')

            self.measured(name, repeat, 'add-1000-paused', add)
            self.measured(name, repeat, 'idle-1000-paused', lambda: time.sleep(self.args.idle_seconds))
        finally:
            self.stop(name)

    def run(self):
        for name in CLIENTS:
            self.stop(name)
        try:
            for repeat in range(self.args.repeat_offset, self.args.repeat_offset + self.args.repeats):
                order = self.args.clients[repeat % len(self.args.clients):] + self.args.clients[:repeat % len(self.args.clients)]
                for name in order:
                    for group in self.args.workloads:
                        if group == 'catalog':
                            self.catalog(name, repeat)
                        else:
                            self.download(name, repeat, group)
            write_json(self.output / 'complete.json', {'ok': True, 'trials': len(self.results),
                       'timeouts': [{k: r[k] for k in ('client', 'repeat', 'workload')}
                                    for r in self.results if r['status'] != 'ok']})
        except BaseException:
            (self.output / 'failure.txt').write_text(traceback.format_exc())
            raise
        finally:
            for name in CLIENTS:
                self.stop(name)
            peer_control([])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--repeat-offset', type=int, default=0)
    parser.add_argument('--clients', nargs='+', choices=list(CLIENTS), default=list(CLIENTS))
    parser.add_argument('--workloads', nargs='+', choices=['large', 'files', 'concurrent', 'shaped', 'catalog'],
                        default=['large', 'files', 'concurrent', 'shaped', 'catalog'])
    parser.add_argument('--idle-seconds', type=float, default=15)
    parser.add_argument('--output', default=datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
    Benchmark(parser.parse_args()).run()
