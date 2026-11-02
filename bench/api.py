"""Small stdlib adapters for the five clients and the Docker Engine API."""
import base64
import http.client
import http.cookiejar
import json
import socket
import urllib.error
import urllib.parse
import urllib.request
import xmlrpc.client

from fixtures import ROOT


class UnixHTTP(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect('/var/run/docker.sock')


def docker(method, path, body=None, raw=False):
    conn = UnixHTTP('localhost', timeout=180)
    data = None if body is None else json.dumps(body).encode()
    conn.request(method, '/v1.47' + path, body=data,
                 headers={'Content-Type': 'application/json'})
    response = conn.getresponse()
    content = response.read()
    conn.close()
    if response.status >= 400:
        raise RuntimeError(f'Docker {method} {path}: {response.status}: {content[:1000]!r}')
    return content if raw else json.loads(content) if content else None


def containers():
    rows = docker('GET', '/containers/json?all=true&filters=' + urllib.parse.quote(
        json.dumps({'label': ['com.docker.compose.project=torrent-bench']})))
    return {r['Labels']['com.docker.compose.service']: r['Id'] for r in rows
            if r['Labels'].get('com.docker.compose.oneoff') == 'False'}


class HTTP:
    def __init__(self, base):
        self.base = base
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(
            http.cookiejar.CookieJar()), urllib.request.ProxyHandler({}))

    def call(self, path, data=None, form=None, value=None, headers=None):
        headers = dict(headers or {})
        if form is not None:
            data = urllib.parse.urlencode(form).encode()
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        if value is not None:
            data = json.dumps(value).encode()
            headers['Content-Type'] = 'application/json'
        request = urllib.request.Request(self.base + path, data=data, headers=headers)
        with self.opener.open(request, timeout=30) as response:
            payload = response.read()
        try:
            return json.loads(payload)
        except (ValueError, UnicodeDecodeError):
            return payload.decode()


class Qbit(HTTP):
    def __init__(self):
        super().__init__('http://qbittorrent:8080/api/v2/')

    def ready(self):
        return self.call('app/version')

    def configure(self):
        settings = dict(dht=False, pex=False, lsd=False, upnp=False,
                        queueing_enabled=False, max_connec=2000, max_connec_per_torrent=100,
                        max_uploads=2000, max_uploads_per_torrent=100,
                        bittorrent_protocol=1, dl_limit=0, up_limit=0)
        self.call('app/setPreferences', form={'json': json.dumps(settings)})
        return {'version': self.ready(), 'build': self.call('app/buildInfo'),
                'preferences': self.call('app/preferences')}

    def add(self, torrent, paused=False):
        boundary = 'torrentbenchboundary'
        content = (ROOT / 'torrents' / (torrent['name'] + '.torrent')).read_bytes()
        fields = {'savepath': '/downloads', 'paused': str(paused).lower(),
                  'stopped': str(paused).lower(), 'autoTMM': 'false'}
        chunks = [f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
                  for k, v in fields.items()]
        chunks += [f'--{boundary}\r\nContent-Disposition: form-data; name="torrents"; filename="fixture.torrent"\r\nContent-Type: application/x-bittorrent\r\n\r\n'.encode(),
                   content, f'\r\n--{boundary}--\r\n'.encode()]
        result = self.call('torrents/add', data=b''.join(chunks),
                           headers={'Content-Type': 'multipart/form-data; boundary=' + boundary})
        if not isinstance(result, dict) or result.get('success_count') != 1:
            raise RuntimeError(result)

    def status(self):
        return [{'id': t['hash'], 'done': t['progress'] >= 1 and t['state'] in
                 ('uploading', 'stalledUP', 'forcedUP', 'queuedUP', 'stoppedUP'), 'bytes': t['completed'],
                 'state': t['state'], 'checking': 'checking' in t['state'].lower(),
                 'paused': t['state'].startswith('stopped'),
                 'error': t['state'] in ('error', 'missingFiles')}
                for t in self.call('torrents/info')]

    def recheck(self, torrent):
        self.call('torrents/recheck', form={'hashes': torrent['hash']})


class Deluge(HTTP):
    def __init__(self):
        super().__init__('http://deluge:8112/json')

    def rpc(self, method, *params):
        r = self.call('', value={'method': method, 'params': list(params), 'id': 1})
        if r.get('error'):
            raise RuntimeError(r['error'])
        return r['result']

    def ready(self):
        assert self.rpc('auth.login', 'deluge')
        if not self.rpc('web.connected'):
            hosts = self.rpc('web.get_hosts')
            self.rpc('web.connect', hosts[0][0])
        return self.rpc('core.get_libtorrent_version')

    def configure(self):
        self.rpc('core.set_config', dict(download_location='/downloads',
                 max_active_limit=2000, max_active_downloading=2000, max_active_seeding=2000,
                 max_connections_global=2000, max_connections_per_torrent=100,
                 max_upload_slots_global=2000, max_upload_slots_per_torrent=100,
                 max_download_speed=-1, max_upload_speed=-1, dht=False, lsd=False,
                 utpex=False, upnp=False, natpmp=False, random_port=False,
                 listen_ports=[6881, 6881], rate_limit_ip_overhead=False))
        return {'version': self.rpc('daemon.get_version'), 'library': self.rpc('core.get_libtorrent_version'),
                'preferences': self.rpc('core.get_config')}

    def add(self, torrent, paused=False):
        data = base64.b64encode((ROOT / 'torrents' / (torrent['name'] + '.torrent')).read_bytes()).decode()
        self.rpc('core.add_torrent_file', torrent['name'] + '.torrent', data,
                 {'download_location': '/downloads', 'add_paused': paused})

    def status(self):
        rows = self.rpc('core.get_torrents_status', {}, ['progress', 'total_done', 'state'])
        return [{'id': key, 'done': t['progress'] >= 100, 'bytes': t['total_done'],
                 'state': t['state'], 'checking': t['state'] == 'Checking',
                 'paused': t['state'] == 'Paused',
                 'error': t['state'] == 'Error'} for key, t in rows.items()]

    def recheck(self, torrent):
        self.rpc('core.force_recheck', [torrent['hash']])


class Transmission(HTTP):
    def __init__(self):
        super().__init__('http://transmission:9091/transmission/rpc')
        self.session = ''

    def rpc(self, method, **args):
        try:
            r = self.call('', value={'method': method, 'arguments': args},
                          headers={'X-Transmission-Session-Id': self.session})
        except urllib.error.HTTPError as e:
            if e.code != 409:
                raise
            self.session = e.headers['X-Transmission-Session-Id']
            return self.rpc(method, **args)
        if r['result'] != 'success':
            raise RuntimeError(r)
        return r['arguments']

    def ready(self):
        return self.rpc('session-get')['version']

    def configure(self):
        self.rpc('session-set', **{'download-dir': '/downloads', 'dht-enabled': False,
                 'pex-enabled': False, 'lpd-enabled': False, 'port-forwarding-enabled': False,
                 'utp-enabled': False, 'peer-port': 6881, 'peer-port-random-on-start': False,
                 'peer-limit-global': 2000, 'peer-limit-per-torrent': 100,
                 'download-queue-enabled': False, 'seed-queue-enabled': False,
                 'speed-limit-down-enabled': False, 'speed-limit-up-enabled': False,
                 'ratio-limit-enabled': False, 'idle-seeding-limit-enabled': False})
        settings = self.rpc('session-get')
        settings.pop('session-id', None)
        return settings

    def add(self, torrent, paused=False):
        data = base64.b64encode((ROOT / 'torrents' / (torrent['name'] + '.torrent')).read_bytes()).decode()
        self.rpc('torrent-add', metainfo=data, paused=paused, **{'download-dir': '/downloads'})

    def status(self):
        rows = self.rpc('torrent-get', fields=['hashString', 'percentDone', 'haveValid', 'status', 'error', 'errorString'])['torrents']
        return [{'id': t['hashString'], 'done': t['percentDone'] >= 1, 'bytes': t['haveValid'],
                 'state': t['status'], 'checking': t['status'] in (1, 2),
                 'paused': t['status'] == 0,
                 'error': t['error'] == 3, 'error_message': t['errorString']}
                for t in rows]

    def recheck(self, torrent):
        self.rpc('torrent-verify', ids=[torrent['hash']])


class Rtorrent:
    def rpc(self, method, *args):
        # rTorrent speaks XML-RPC over SCGI, so no proxy/web server is required.
        body = xmlrpc.client.dumps(args, methodname=method, allow_none=True).encode()
        headers = b'CONTENT_LENGTH\x00' + str(len(body)).encode() + b'\x00SCGI\x001\x00'
        wire = str(len(headers)).encode() + b':' + headers + b',' + body
        with socket.create_connection(('rtorrent', 5000), timeout=30) as conn:
            conn.sendall(wire)
            chunks = []
            while data := conn.recv(65536):
                chunks.append(data)
        payload = b''.join(chunks).split(b'\r\n\r\n', 1)[-1]
        return xmlrpc.client.loads(payload)[0][0]

    def ready(self):
        return self.rpc('system.client_version')

    def configure(self):
        return {'version': self.ready(), 'library': self.rpc('system.library_version')}

    def add(self, torrent, paused=False):
        method = 'load.normal' if paused else 'load.start'
        self.rpc(method, '', '/fixtures/torrents/' + torrent['name'] + '.torrent')

    def status(self):
        rows = self.rpc('d.multicall2', '', 'main', 'd.hash=', 'd.complete=',
                        'd.completed_bytes=', 'd.hashing=', 'd.message=', 'd.is_active=')
        return [{'id': t[0].lower(), 'done': bool(t[1]), 'bytes': t[2], 'state': t[4],
                 'checking': t[3] != 0, 'paused': not t[5], 'error': bool(t[4])} for t in rows]

    def recheck(self, torrent):
        self.rpc('d.check_hash', torrent['hash'].upper())


class Rqbit(HTTP):
    def __init__(self):
        super().__init__('http://rqbit:3030')

    def ready(self):
        return self.call('/')['version']

    def configure(self):
        return self.call('/')

    def add(self, torrent, paused=False):
        self.call('/torrents?overwrite=true',
                  data=(ROOT / 'torrents' / (torrent['name'] + '.torrent')).read_bytes())
        if paused:
            self.call('/torrents/' + torrent['hash'] + '/pause', data=b'')

    def status(self):
        rows = self.call('/torrents?with_stats=true')['torrents']
        result = []
        for row in rows:
            t = row['stats']
            result.append({'id': row['info_hash'], 'done': t['finished'],
                           'bytes': t['progress_bytes'], 'state': t['state'],
                           'paused': t['state'] == 'paused',
                           'checking': t['state'] == 'initializing', 'error': t['state'] == 'error'})
        return result

    def recheck(self, torrent):
        # No force-recheck endpoint: forget and re-add existing data, forcing its init hash check.
        self.call('/torrents/' + torrent['hash'] + '/forget', data=b'')
        self.add(torrent)


CLIENTS = {'qbittorrent': Qbit, 'deluge': Deluge, 'transmission': Transmission,
           'rtorrent': Rtorrent, 'rqbit': Rqbit}
