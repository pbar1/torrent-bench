#!/bin/sh
set -eu
cd "$(dirname "$0")"

compose() { docker compose -p torrent-bench-ubuntu --env-file images.env -f compose.yaml -f compose.ubuntu.yaml "$@"; }
cleanup() { compose down --volumes --remove-orphans; }
trap cleanup EXIT INT TERM

compose build rtorrent aria2
compose run --rm --no-deps bench python /bench/test_results.py
compose run --rm --no-deps bench python /bench/test_ubuntu.py
compose run --rm --no-deps bench python /bench/test_ubuntu_results.py
compose create --force-recreate qbittorrent deluge transmission rtorrent rqbit aria2
compose run --rm --no-deps bench python -u /bench/ubuntu_run.py "$@"
