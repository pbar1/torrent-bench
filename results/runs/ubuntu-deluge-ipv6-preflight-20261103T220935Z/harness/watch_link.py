"""macOS host-side, address-free Ethernet/route observations for a long run."""
import argparse
import datetime
import json
import subprocess
import time
from pathlib import Path


def observe(interface):
    row = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'interface': interface}
    try:
        for family in ('inet', 'inet6'):
            routes = subprocess.check_output(['netstat', '-rn', '-f', family], text=True)
            row[family + '_default_interfaces'] = [line.split()[3] if family == 'inet' else line.split()[-1]
                for line in routes.splitlines() if line.startswith('default')
                and 'I' not in line.split()[2] and 'G' in line.split()[2]]
        raw = subprocess.check_output(['ifconfig', interface], text=True)
        row['media'] = next(line.split('media:', 1)[1].strip() for line in raw.splitlines() if 'media:' in line)
        row['status'] = next(line.split('status:', 1)[1].strip() for line in raw.splitlines() if 'status:' in line)
        row['ok'] = (row['status'] == 'active' and '1000baseT <full-duplex>' in row['media']
                     and all(row[f + '_default_interfaces'] == [interface] for f in ('inet', 'inet6')))
    except Exception as error:
        row.update(ok=False, error_type=type(error).__name__)
    return row


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    parser.add_argument('--interface', default='en9')
    parser.add_argument('--interval', type=float, default=10)
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    previous = None
    try:
        while True:
            row = observe(args.interface)
            with (args.directory / 'host-link.jsonl').open('a') as handle:
                handle.write(json.dumps(row) + '\n')
            if row['ok'] != previous:
                print(json.dumps(row), flush=True)
                previous = row['ok']
            time.sleep(args.interval)
    except KeyboardInterrupt:
        row = observe(args.interface)
        with (args.directory / 'host-link.jsonl').open('a') as handle:
            handle.write(json.dumps(row) + '\n')
        print('Host link monitor stopped.', flush=True)
