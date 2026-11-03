#!/bin/sh
set -eu
cd "$(dirname "$0")"
task_output=${1:?Supply an unused output name}
shift
task_preflight="runs/${task_output}-preflight-$(date -u +%Y%m%dT%H%M%SZ)"

compose() { docker compose -p torrent-bench-ubuntu --env-file images.env -f compose.yaml -f compose.ubuntu.yaml -f compose.deluge-ipv6.yaml "$@"; }
cleanup() { compose down --volumes --remove-orphans; }
trap cleanup EXIT INT TERM

compose build rtorrent aria2
compose create --force-recreate qbittorrent deluge transmission rtorrent rqbit aria2
compose run --rm --no-deps bench python /bench/preflight_deluge_interface.py --output "$task_preflight" --study-output "$task_output"
compose run --rm --no-deps bench python -u /bench/ubuntu_run.py --output "$task_output" --clients deluge --repeats 6 --timeout 900 --stall-seconds 0 "$@"
