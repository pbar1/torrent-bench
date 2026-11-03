#!/bin/sh
set -eu
/lsiopy/bin/python3 - <<'PY'
import json
from pathlib import Path

routes = [line.split() for line in Path('/proc/net/route').read_text().splitlines()[1:]]
interfaces = [row[0] for row in routes if row[1] == '00000000' and int(row[3], 16) & 2]
assert len(interfaces) == 1, 'Expected one outgoing default-route interface'
path = Path('/config/core.conf')
decoder = json.JSONDecoder()
text = path.read_text().lstrip()
header, end = decoder.raw_decode(text)
preferences, _ = decoder.raw_decode(text[end:].lstrip())
preferences['listen_interface'] = interfaces[0]
path.write_text(json.dumps(header) + '\n' + json.dumps(preferences) + '\n')
print('Deluge BitTorrent listen interface: ' + interfaces[0], flush=True)
PY
