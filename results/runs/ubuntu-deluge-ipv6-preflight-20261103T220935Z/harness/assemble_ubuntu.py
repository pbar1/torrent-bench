"""Join disjoint public-test batches, preserving every measured trial and sample."""
import argparse
import gzip
import json
import shutil
from pathlib import Path

from summarize_ubuntu import summarize


def read(path, name):
    return json.loads((path / name).read_text())


def write(path, name, value):
    (path / name).write_text(json.dumps(value, indent=2) + '\n')


def assemble(first, second, output):
    if output.exists():
        raise FileExistsError('Choose an unused output directory')
    sources = [first, second]
    envs = [read(p, 'environment.json') for p in sources]
    batches = [read(p, 'trials.json') for p in sources]
    trials = [t for batch in batches for t in batch]
    clients = list(envs[0]['containers'])
    assert len(clients) == 6 and len(trials) == 6
    assert {(t['client'], t['repeat'], t['workload']) for t in trials} == {
        (c, 0, 'ubuntu-public') for c in clients}
    for name in ('fixtures-manifest.json', 'torrent-source.json'):
        assert (first / name).read_bytes() == (second / name).read_bytes()
    for field in ('NCPU', 'MemTotal', 'KernelVersion', 'OperatingSystem', 'Architecture',
                  'ServerVersion', 'Driver', 'CgroupVersion', 'host_link', 'public_network'):
        assert envs[0][field] == envs[1][field], field
    for field in ('timeout', 'stall_seconds', 'repeats'):
        assert envs[0]['arguments'][field] == envs[1]['arguments'][field], field
    for client in clients:
        a, b = (e['containers'][client] for e in envs)
        for field in ('image_ref', 'architecture', 'host_config', 'command'):
            assert a[field] == b[field], (client, field)
        # Local rebuild attestations change image IDs; use the actually measured
        # batch's image below. The other four images are immutable digest pins.
        if client not in ('rtorrent', 'aria2'):
            assert a['image_id'] == b['image_id'], client
    assert read(second, 'complete.json')['ok']
    output.mkdir(parents=True)
    environment = dict(envs[0])
    environment['containers'] = {t['client']: e['containers'][t['client']]
                                  for e, batch in zip(envs, batches) for t in batch}
    environment.pop('harness_sha256')
    environment['arguments'] = {**envs[0]['arguments'], 'clients': clients, 'output': output.name}
    environment['source_environments'] = {str(p): e for p, e in zip(sources, envs)}
    environment['assembly'] = ('Disjoint batches: retain qBittorrent, Deluge, Transmission; '
                               'after correcting rTorrent startup, run rTorrent, rqbit, aria2. '
                               'No successful or timed-out measured attempt was replaced.')
    write(output, 'environment.json', environment)
    write(output, 'trials.json', trials)
    for name in ('fixtures-manifest.json', 'torrent-source.json'):
        shutil.copyfile(first / name, output / name)
    observations, selection = [], []
    with (output / 'samples.jsonl.gz').open('wb') as handle:
        with gzip.GzipFile(filename='', fileobj=handle, mode='wb', mtime=0) as compressed:
            for source, batch in zip(sources, batches):
                plain = source / 'samples.jsonl'
                opener, path = (open, plain) if plain.exists() else (gzip.open, source / 'samples.jsonl.gz')
                with opener(path, 'rb') as samples:
                    shutil.copyfileobj(samples, compressed)
                for t in batch:
                    name = t['client'] + '-effective-settings.json'
                    shutil.copyfile(source / name, output / name)
                    selection.append({'client': t['client'], 'repeat': t['repeat'], 'source': str(source)})
                link_file = source / 'host-link-observations.json'
                if link_file.exists():
                    observations += read(source, link_file.name)
    write(output, 'selection.json', selection)
    write(output, 'host-link-observations.json', observations)
    empty = read(second, 'complete.json')['scratch_empty'] and all(
        t['cleanup']['remaining_entries'] == 0 and not t['cleanup']['iso_retained'] for t in trials)
    write(output, 'complete.json', {'ok': True, 'trials': len(trials), 'scratch_empty': empty,
        'timeouts': [{k: t[k] for k in ('client', 'repeat', 'workload')}
                     for t in trials if t['status'] != 'ok']})
    summarize(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('first', type=Path)
    parser.add_argument('second', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    assemble(args.first, args.second, args.output)
