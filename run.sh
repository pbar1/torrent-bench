#!/bin/sh
set -eu
cd "$(dirname "$0")"

compose() { docker compose --env-file images.env "$@"; }
cleanup() { compose stop qbittorrent deluge transmission rtorrent rqbit peer1 peer2 leech1 leech2 tracker; }
trap cleanup EXIT INT TERM

compose build rtorrent
compose run --rm --no-deps bench python /bench/test_results.py
compose run --rm --no-deps bench python -u /bench/fixtures.py
compose run --rm --no-deps --entrypoint /lsiopy/bin/python3 peer1 /bench/test_fixtures.py
compose create --force-recreate
compose start tracker peer1 peer2 leech1 leech2
compose run --rm --no-deps bench python -u /bench/run.py "$@"
