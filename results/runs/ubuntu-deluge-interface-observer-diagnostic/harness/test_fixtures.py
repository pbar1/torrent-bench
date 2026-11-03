"""Check fixture invariants against libtorrent (run in the reference-peer image)."""
import hashlib
import json
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer

import libtorrent as lt

from fixtures import ROOT, bencode
from tracker import KNOWN, PEERS, Tracker


class FixturesTest(unittest.TestCase):
    def test_bencode_canonical(self):
        self.assertEqual(bencode({'z': 1, 'a': [b'x', 2]}), b'd1:al1:xi2ee1:zi1ee')

    def test_all_torrents_are_private_and_local(self):
        manifest = json.loads((ROOT / 'manifest.json').read_text())
        for t in manifest:
            ti = lt.torrent_info(str(ROOT / 'torrents' / (t['name'] + '.torrent')))
            self.assertTrue(ti.priv())
            self.assertEqual(str(ti.info_hash()), t['hash'])
            self.assertEqual(ti.total_size(), t['bytes'])
            self.assertEqual([x.url for x in ti.trackers()], ['http://tracker:8080/announce'])

    def test_multifile_piece_hashes_and_paths(self):
        ti = lt.torrent_info(str(ROOT / 'torrents/files.torrent'))
        files = ti.files()
        piece = bytearray()
        hashes = []
        for i in range(files.num_files()):
            with (ROOT / 'source' / files.file_path(i)).open('rb') as f:
                while chunk := f.read(ti.piece_length()):
                    piece.extend(chunk)
                    if len(piece) == ti.piece_length():
                        hashes.append(hashlib.sha1(piece).digest())
                        piece.clear()
        self.assertFalse(piece)
        self.assertEqual(len(hashes), ti.num_pieces())
        self.assertEqual(hashes, [ti.hash_for_piece(i) for i in range(ti.num_pieces())])

    def test_tracker_announce_scrape_and_reject_unknown_hash(self):
        PEERS.clear()
        server = ThreadingHTTPServer(('127.0.0.1', 0), Tracker)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        key = sorted(KNOWN)[0]

        def get(path, **query):
            with urllib.request.urlopen(base + path + '?' + urllib.parse.urlencode(query)) as response:
                return lt.bdecode(response.read())

        try:
            first = get('/announce', info_hash=key, port=6881, left=0)
            self.assertEqual(first[b'peers'], b'')
            second = get('/announce', info_hash=key, port=6882, left=1)
            self.assertEqual(second[b'peers'], bytes([127, 0, 0, 1, 0x1a, 0xe1]))
            scrape = get('/scrape', info_hash=key)[b'files'][key]
            self.assertEqual(scrape[b'complete'], 1)
            self.assertEqual(scrape[b'incomplete'], 1)
            self.assertEqual(len(PEERS[key]), 2)
            get('/announce', info_hash=key, port=6882, left=0, role='leecher')
            third = get('/announce', info_hash=key, port=6883, left=1, role='leecher')
            self.assertEqual(third[b'peers'], bytes([127, 0, 0, 1, 0x1a, 0xe1]))
            normal = get('/announce', info_hash=key, port=6881, left=0)
            self.assertEqual(len(normal[b'peers']), 12)
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                get('/announce', info_hash=bytes(20), port=6881)
            self.assertEqual(ctx.exception.code, 403)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
