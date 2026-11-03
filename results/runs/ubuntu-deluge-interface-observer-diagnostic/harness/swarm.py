"""Libtorrent reference peer with a local control API; seed or verified leecher."""
import json
import shutil
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import libtorrent as lt

from fixtures import ROOT

HANDLES = []
SESSION = lt.session({
    'listen_interfaces': '0.0.0.0:6881', 'outgoing_interfaces': 'eth0',
    'enable_dht': False, 'enable_lsd': False,
    'enable_upnp': False, 'enable_natpmp': False, 'enable_incoming_utp': False,
    'enable_outgoing_utp': False, 'connections_limit': 2000,
    'listen_queue_size': 2048, 'connection_speed': 2000,
    'out_enc_policy': int(lt.enc_policy.disabled), 'in_enc_policy': int(lt.enc_policy.disabled),
    'active_downloads': 2000, 'active_seeds': 2000, 'active_limit': 2000,
    'unchoke_slots_limit': 2000, 'ignore_limits_on_local_network': False,
    'rate_limit_ip_overhead': False,
    'alert_mask': int(lt.alert.category_t.error_notification | lt.alert.category_t.peer_notification
                      | lt.alert.category_t.connect_notification),
})


class Control(BaseHTTPRequestHandler):
    def do_POST(self):
        global HANDLES
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        for handle in HANDLES:
            SESSION.remove_torrent(handle)
        HANDLES = []
        # Wait for old handles to release files before deleting the scratch directory.
        time.sleep(0.2)
        shutil.rmtree('/scratch/downloads', ignore_errors=True)
        Path('/scratch/downloads').mkdir(parents=True)
        SESSION.apply_settings({'upload_rate_limit': body.get('rate', 0)})
        mode = body.get('mode', 'seed')
        for name in body.get('names', []):
            params = lt.add_torrent_params()
            params.ti = lt.torrent_info(str(ROOT / 'torrents' / (name + '.torrent')))
            params.save_path = '/fixtures/source' if mode == 'seed' else '/scratch/downloads'
            params.flags &= ~lt.torrent_flags.auto_managed
            params.flags &= ~lt.torrent_flags.paused
            if mode == 'seed':
                # Input hashes are generated locally; no expensive per-trial source recheck.
                params.flags |= lt.torrent_flags.seed_mode
            else:
                # A role-aware local tracker allows the tested client to dial
                # leechers, while never exposing one leecher to the other.
                params.flags |= lt.torrent_flags.override_trackers
                params.flags |= lt.torrent_flags.disable_pex
                params.trackers = ['http://tracker:8080/announce?role=leecher']
            h = SESSION.add_torrent(params)
            HANDLES.append(h)
        self.reply({'ok': True, 'libtorrent': lt.__version__})

    def do_GET(self):
        for alert in SESSION.pop_alerts():
            if isinstance(alert, (lt.peer_disconnected_alert, lt.peer_error_alert, lt.file_error_alert)):
                print(str(alert), flush=True)
        statuses = [h.status() for h in HANDLES]
        self.reply({'libtorrent': lt.__version__, 'count': len(statuses),
                    'done': sum(s.is_seeding for s in statuses),
                    'bytes': sum(s.total_wanted_done for s in statuses),
                    'downloaded': sum(s.total_payload_download for s in statuses),
                    'uploaded': sum(s.total_payload_upload for s in statuses),
                    'failed_bytes': sum(s.total_failed_bytes for s in statuses),
                    'peers': sum(s.num_peers for s in statuses),
                    'states': [str(s.state) for s in statuses],
                    'peer_details': [{'ip': p.ip, 'client': str(p.client), 'flags': int(p.flags),
                                      'down_speed': p.down_speed, 'up_speed': p.up_speed}
                                     for h in HANDLES[:1] for p in h.get_peer_info()],
                    'errors': [str(s.errc.message()) for s in statuses if s.errc.value()]})

    def reply(self, value):
        data = json.dumps(value).encode()
        self.send_response(200)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


print('reference libtorrent', lt.__version__, flush=True)
HTTPServer(('0.0.0.0', 8080), Control).serve_forever()
