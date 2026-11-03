"""Deterministic, private v1 torrents. No external data or dependencies."""
import hashlib
import json
import os
from pathlib import Path

ROOT = Path('/fixtures')
MIB = 1024 ** 2


def bencode(x):
    if isinstance(x, int):
        return b'i' + str(x).encode() + b'e'
    if isinstance(x, str):
        x = x.encode()
    if isinstance(x, bytes):
        return str(len(x)).encode() + b':' + x
    if isinstance(x, list):
        return b'l' + b''.join(map(bencode, x)) + b'e'
    return b'd' + b''.join(bencode(k) + bencode(v) for k, v in sorted(x.items())) + b'e'


def generate():
    ROOT.mkdir(exist_ok=True)
    specs = [('large', 1, 4096 * MIB, MIB),
             ('files', 2048, MIB // 2, MIB // 4),
             ('shaped', 1, 1024 * MIB, MIB)]
    specs += [(f'concurrent-{i:03}', 1, 16 * MIB, MIB // 4) for i in range(64)]
    specs += [(f'catalog-{i:04}', 1, 64 * 1024, 64 * 1024) for i in range(1000)]
    manifest = []
    for name, count, size, piece in specs:
        group = name.split('-')[0]
        # Each file/block gets distinct deterministic, nonzero bytes.
        files, hashes, pieces = [], [], bytearray()
        for i in range(count):
            rel = name + '.bin' if count == 1 else f'{name}/dir-{i // 64:03}/file-{i:04}.bin'
            path = ROOT / 'source' / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            sha = hashlib.sha256()
            with path.open('wb') as f:
                remaining = size
                offset = 0
                while remaining:
                    seed = f'torrent-bench-v1:{name}:{i}:{offset}'.encode()
                    data = hashlib.shake_256(seed).digest(min(MIB, remaining))
                    f.write(data)
                    sha.update(data)
                    # All fixture file lengths are multiples of their piece lengths.
                    for j in range(0, len(data), piece):
                        pieces.extend(hashlib.sha1(data[j:j + piece]).digest())
                    remaining -= len(data)
                    offset += len(data)
            files.append({'path': rel, 'bytes': size, 'sha256': sha.hexdigest()})
            hashes.append({'length': size, 'path': rel.split('/')[1:]})
        info = {'name': name + '.bin' if count == 1 else name,
                'piece length': piece, 'pieces': bytes(pieces), 'private': 1}
        info.update({'length': size} if count == 1 else {'files': hashes})
        torrent = {'announce': 'http://tracker:8080/announce', 'info': info,
                   'created by': 'torrent-client-benchmarks synthetic v1'}
        torrent_path = ROOT / 'torrents' / (name + '.torrent')
        torrent_path.parent.mkdir(exist_ok=True)
        torrent_path.write_bytes(bencode(torrent))
        manifest.append({'name': name, 'group': group, 'bytes': count * size,
                         'hash': hashlib.sha1(bencode(info)).hexdigest(), 'files': files})
        if name in ('large', 'files', 'shaped'):
            print('generated', name, count * size, flush=True)
    (ROOT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    # Fixtures are mounted read-only in clients/reference peers that use them.
    os.sync()
    print(f'Generated {len(manifest)} private torrents', flush=True)


if __name__ == '__main__':
    generate()
