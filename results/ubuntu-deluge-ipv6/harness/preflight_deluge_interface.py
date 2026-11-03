"""Check the follow-up's sockets before any timed download; record its plan."""
import argparse
import datetime
import hashlib
import json
import shutil
import time
from pathlib import Path
from types import SimpleNamespace

from api import docker
from ubuntu_run import UbuntuBenchmark, clear_payload, write_json


def preflight(output, study_output):
    args = SimpleNamespace(output=output, clients=['deluge'], repeats=1, timeout=900,
                           stall_seconds=0, order_seed=20261103, preflight=True,
                           host_interface='not recorded', host_link='not recorded')
    bench = UbuntuBenchmark(args)
    try:
        client = bench.start('deluge', public=True)
        client.add(bench.torrent, paused=True)
        deadline = time.monotonic() + 10
        while True:
            rows = [r for r in client.status() if r['id'] == bench.torrent['hash']]
            if rows and all(r['paused'] for r in rows):
                break
            assert time.monotonic() < deadline, 'Paused preflight torrent did not become ready'
            time.sleep(0.1)
        assert all(r['bytes'] == 0 for r in rows)
        probe = '''import json,pathlib
print(json.dumps({proto:sum(int(line.split()[1].split(':')[1],16)==6881
for line in pathlib.Path('/proc/net/'+proto).read_text().splitlines()[1:])
for proto in ('tcp','tcp6','udp','udp6')}))'''
        execution = docker('POST', '/containers/' + bench.ids['deluge'] + '/exec',
                           {'AttachStdout': True, 'AttachStderr': True, 'Tty': True,
                            'Cmd': ['/lsiopy/bin/python3', '-c', probe]})
        raw = docker('POST', '/exec/' + execution['Id'] + '/start',
                     {'Detach': False, 'Tty': True}, raw=True)
        sockets = json.loads(raw)
        assert all(sockets[k] > 0 for k in ('tcp', 'tcp6', 'udp', 'udp6')), sockets
        settings = json.loads((bench.output / 'deluge-effective-settings.json').read_text())
        interface = settings['preferences']['listen_interface']
        assert interface and interface != '0.0.0.0'
        evidence = {'ok': True, 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    'listen_interface': interface, 'port_6881_socket_entries': sockets,
                    'torrent_paused': True, 'performance_measurement': False}
        write_json(bench.output / 'preflight.json', evidence)
        native = Path('/results/ubuntu-six-runs')
        assert json.loads((native / 'complete.json').read_text())['ok']
        native_trials = json.loads((native / 'trials.json').read_text())
        deluge = [t for t in native_trials if t['client'] == 'deluge']
        assert len(native_trials) == 36 and len(deluge) == 6
        assert sum(t['status'] == 'ok' for t in deluge) < 3
        native_env = json.loads((native / 'environment.json').read_text())
        study = {
            'registered_utc': evidence['utc'], 'classification': 'exploratory interface follow-up',
            'native_cohort': '../ubuntu-six-runs',
            'native_trials_sha256': hashlib.sha256((native / 'trials.json').read_bytes()).hexdigest(),
            'planned_attempts': 6, 'deadline_s': 900, 'early_stall_cutoff': None,
            'condition': 'Set listen_interface to the outgoing default-route interface; other client settings stay the same.',
            'observer_amendment': 'Disable optional discovery RPCs after an excluded diagnostic run exposed blocking timeouts. Basic status polling and resource measurement are unchanged.',
            'excluded_observer_diagnostic': '../runs/ubuntu-deluge-interface-observer-diagnostic',
            'listen_interface': interface, 'preflight': output + '/preflight.json',
            'preflight_sha256': hashlib.sha256((bench.output / 'preflight.json').read_bytes()).hexdigest(),
            'same_deluge_image_id': native_env['containers']['deluge']['image_id'],
            'stopping_rule': 'Execute all six attempts once; retain failures; do not pool with the native cohort.',
            'comparison_scope': 'A different configuration in a later window; no contemporaneous head-to-head speed claim.',
            'profile_sha256': {name: hashlib.sha256(source.read_bytes()).hexdigest()
                               for name, source in (
                                   ('compose.deluge-ipv6.yaml', Path('/study-profile.yaml')),
                                   ('bench/deluge-ipv6-init.sh', Path('/bench/deluge-ipv6-init.sh')))}}
        target = Path('/results') / study_output
        target.mkdir(parents=True, exist_ok=True)
        assert not (target / 'trials.json').exists()
        for name, source in (('compose.deluge-ipv6.yaml', Path('/study-profile.yaml')),
                             ('bench/deluge-ipv6-init.sh', Path('/bench/deluge-ipv6-init.sh'))):
            archived = target / 'profile' / name
            archived.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, archived)
        write_json(target / 'study.json', study)
        print(json.dumps(evidence), flush=True)
    finally:
        try:
            bench.stop('deluge')
        finally:
            clear_payload()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--study-output', required=True)
    args = parser.parse_args()
    preflight(args.output, args.study_output)
