"""Aggregate peer/discovery counters without recording peer addresses or IDs."""
import ipaddress
import os


def families(addresses):
    result = {'ipv4': 0, 'ipv6': 0, 'unknown': 0}
    for address in addresses:
        value = str(address)
        if value.startswith('['):
            value = value[1:].split(']', 1)[0]
        elif value.count(':') == 1:
            value = value.split(':', 1)[0]
        try:
            version = ipaddress.ip_address(value.split('%', 1)[0]).version
            result['ipv' + str(version)] += 1
        except ValueError:
            result['unknown'] += 1
    return result


def diagnostics(client, name, torrent):
    if os.environ.get('BENCHMARK_SKIP_DISCOVERY_RPC') == '1':
        return {'not_collected': 'Optional discovery RPCs disabled for this profile'}
    key = torrent['hash']
    if name == 'qbittorrent':
        rows = client.call('torrents/info?hashes=' + key)
        peers = client.call('sync/torrentPeers?hash=' + key).get('peers', {})
        row = rows[0] if rows else {}
        return {'peer_families': families(p['ip'] for p in peers.values()),
                'seeds': row.get('num_seeds'), 'leechers': row.get('num_leechs'),
                'dht_nodes': client.call('transfer/info').get('dht_nodes')}
    if name == 'deluge':
        rows = client.rpc('core.get_torrents_status', {},
                          ['num_peers', 'num_seeds', 'tracker_status', 'peers'])
        row = rows.get(key, {})
        return {'peers': row.get('num_peers'), 'seeds': row.get('num_seeds'),
                'peer_families': families(p['ip'] for p in row.get('peers', [])),
                'tracker_ok': row.get('tracker_status') == 'Announce OK',
                'dht': client.rpc('core.get_session_status', ['dht.dht_nodes'])}
    if name == 'transmission':
        rows = client.rpc('torrent-get', ids=[key],
                          fields=['peersConnected', 'peersFrom', 'peers', 'trackerStats'])['torrents']
        row = rows[0] if rows else {}
        return {'peers': row.get('peersConnected'), 'peer_sources': row.get('peersFrom'),
                'peer_families': families(p['address'] for p in row.get('peers', [])),
                'trackers': [{'success': t['lastAnnounceSucceeded'],
                              'returned_peers': t['lastAnnouncePeerCount']}
                             for t in row.get('trackerStats', [])]}
    if name == 'rtorrent':
        peers = client.rpc('p.multicall', key.upper(), '', 'p.address=')
        trackers = client.rpc('t.multicall', key.upper(), '', 't.type=',
                              't.success_counter=', 't.failed_counter=', 't.latest_sum_peers=')
        return {'peer_families': families(p[0] for p in peers),
                'dht': client.rpc('dht.statistics'), 'trackers': trackers}
    if name == 'aria2':
        gid = client.gids[key]
        row = client.rpc('aria2.tellStatus', gid, ['status', 'connections', 'numSeeders', 'downloadSpeed'])
        peers = client.rpc('aria2.getPeers', gid) if row['status'] == 'active' else []
        return {'peers': int(row.get('connections', 0)), 'seeds': int(row.get('numSeeders', 0)),
                'download_bytes_s': int(row.get('downloadSpeed', 0)),
                'peer_families': families(p['ip'] for p in peers)}
    if name == 'rqbit':
        rows = client.call('/torrents?with_stats=true')['torrents']
        row = next(r['stats'] for r in rows if r['info_hash'] == key)
        # Restrict output to aggregate fields; never copy an unfiltered stats tree.
        live = row.get('live') or {}
        snapshot = live.get('snapshot') or {}
        peers = snapshot.get('peer_stats') or {}
        return {'state': row.get('state'), 'peer_counters': {
            k: v for k, v in peers.items() if isinstance(v, (int, float))}}
    raise ValueError(name)
