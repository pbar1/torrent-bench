"""Closed HTTP tracker: only known fixture hashes and private IPv4 peers."""
import ipaddress
import json
import socket
import struct
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote_to_bytes

from fixtures import ROOT, bencode

KNOWN = {bytes.fromhex(t['hash']) for t in json.loads((ROOT / 'manifest.json').read_text())}
PEERS = {}
LOCK = threading.Lock()


class Tracker(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            data = b'ok'
        else:
            query = {k: unquote_to_bytes(v) for k, v in
                     (part.split('=', 1) for part in self.path.split('?', 1)[-1].split('&') if '=' in part)}
            key = query.get('info_hash')
            ip = self.client_address[0]
            if key not in KNOWN or not ipaddress.ip_address(ip).is_private:
                self.send_error(403)
                return
            if self.path.split('?', 1)[0] == '/scrape':
                with LOCK:
                    now = time.monotonic()
                    active = [seed for last, seed, _ in PEERS.get(key, {}).values() if now - last < 90]
                data = bencode({'files': {key: {'complete': sum(active), 'downloaded': 0,
                                                'incomplete': sum(not s for s in active)}}})
                self.respond(data)
                return
            port = int(query.get('port', b'0'))
            if not 1 <= port <= 65535:
                self.send_error(400)
                return
            with LOCK:
                peers = PEERS.setdefault(key, {})
                now = time.monotonic()
                role = query.get('role', b'client')
                peers[(ip, port)] = (now, int(query.get('left', b'1')) == 0, role)
                if query.get('event') == b'stopped':
                    peers.pop((ip, port), None)
                active = [(addr, seed, other_role) for addr, (last, seed, other_role)
                          in peers.items() if now - last < 90]
            compact = b''.join(socket.inet_aton(addr[0]) + struct.pack('!H', addr[1])
                               for addr, _, other_role in active if addr != (ip, port)
                               and not (role == other_role == b'leecher'))
            data = bencode({'interval': 10, 'min interval': 1, 'peers': compact,
                            'complete': sum(seed for _, seed, _ in active),
                            'incomplete': sum(not seed for _, seed, _ in active)})
        self.respond(data)

    def respond(self, data):
        self.send_response(200)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', 8080), Tracker).serve_forever()
