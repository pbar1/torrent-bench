# Synthetic torrent client benchmark

A closed Docker Compose lab for qBittorrent, Deluge, Transmission, rTorrent, and
rqbit. It generates every payload and `.torrent` locally. There are no public
torrents, magnets, internet trackers, published ports, or internet-connected
runtime networks.

Open [index.html](index.html) directly in a browser for the complete findings,
interactive throughput chart, and all 50 workload groups. It works offline with
no server or build step.

The narrative source is [REPORT.md](REPORT.md), with
[all result tables](results/comparison/SUMMARY.md) and
[the audit totals](results/comparison/validation.json). The accepted measurements
contain 150 phases and 225 GiB of synthetic transfers, across three repetitions
per client.

## Run

Requires a local Docker Engine/Desktop with Compose, native amd64 or arm64,
8 CPUs, about 8 GiB of VM memory, and 25 GiB of available Docker volume storage.
Image pulls and the rTorrent build need internet access; the benchmark does not.

```sh
./run.sh --output my-run --repeats 3
```

The default suite takes tens of minutes. It writes `results/<output>/` and
stops its containers when done. Choose an unused output name; existing trials
are never overwritten. Source payloads, client data, and configuration
live in Docker named volumes, avoiding macOS shared-folder performance effects.
Only scripts and results use host mounts. Each trial starts with clean client
configuration and destination files. Never run two copies of this lab together:
the runner controls the containers in the `torrent-bench` Compose project.

Generate the result tables after a successful run:

```sh
python3 bench/summarize.py results/my-run
python3 bench/validate_results.py results/my-run
```

The validator expects the full five-client suite with three repetitions by
default; pass `--repeats` when auditing a different repeat count.

For a shorter run, or a subset:

```sh
./run.sh --output short --repeats 1 --idle-seconds 3 \
  --clients qbittorrent deluge transmission rtorrent rqbit \
  --workloads large files concurrent shaped catalog
```

Manual steps, if preferred:

```sh
docker compose --env-file images.env build rtorrent
docker compose --env-file images.env run --rm --no-deps bench python /bench/fixtures.py
docker compose --env-file images.env create --force-recreate
docker compose --env-file images.env start tracker peer1 peer2 leech1 leech2
docker compose --env-file images.env run --rm --no-deps bench \
  python -u /bench/run.py --output my-run --repeats 3
docker compose --env-file images.env stop
```

The runner mounts the Docker socket to start/stop **this project's** clients and
read resource counters. This grants the runner Docker daemon access. It creates
no privileged containers and does not change host sysctls, drop host caches, or
stop unrelated containers. If Docker's socket is elsewhere, set `DOCKER_SOCKET`
to its path **on the daemon host**. Docker Desktop normally exposes
`/var/run/docker.sock` inside its Linux VM.

To remove this lab's data after inspecting the results:

```sh
docker compose --env-file images.env down --volumes
```

## Images and provenance

Stable versions were resolved on **2026-11-02** and checked by running their
binaries. `images.env` pins immutable multi-platform image manifest digests;
`environment.json` additionally records the actual platform image IDs. No
emulation is requested.

| Client | Version | Image/source | Provenance |
|---|---|---|---|
| qBittorrent | 5.3.0 | `qbittorrentofficial/qbittorrent-nox` | Upstream official image |
| Deluge | 2.2.0 | `lscr.io/linuxserver/deluge` | Maintained community image, libtorrent 2.0.13 |
| Transmission | 4.1.4 | `lscr.io/linuxserver/transmission` | Maintained community image |
| rTorrent | 0.16.27 | Local `rtorrent/Dockerfile` | Unpatched upstream release, matching Rakshasa libtorrent |
| rqbit | 9.1.0 | `ikatson/rqbit` | Upstream author's image |

rTorrent's Docker wiki explicitly identifies its linked image as community
maintained. A small source build lets this suite use the current release rather
than an older bundled rTorrent/ruTorrent distribution. Both upstream tarballs
are SHA-256 checked against the release asset digests. The Alpine base is pinned,
and every build/runtime APK version is locked to the measured inventory in
`rtorrent/apk-build.lock` and `rtorrent/apk-runtime.lock`. Rebuilding requires
those versions to remain available; missing versions fail the build rather than
silently upgrading dependencies. Measured executable/library hashes are retained
in `rtorrent/measured-binaries.sha256`. A clean rebuild with the package locks
produced identical executable and libtorrent hashes. Build attestations and
image metadata may differ between rebuilds. Other clients and reference peers
use pinned prebuilt images.

Primary references:

- [qBittorrent downloads](https://www.qbittorrent.org/download),
  [official image repository](https://github.com/qbittorrent/docker-qbittorrent-nox)
- [Deluge release](https://pypi.org/project/deluge/2.2.0/),
  [LinuxServer image](https://docs.linuxserver.io/images/docker-deluge/)
- [Transmission 4.1.4](https://github.com/transmission/transmission/releases/tag/4.1.4),
  [LinuxServer image](https://docs.linuxserver.io/images/docker-transmission/)
- [rTorrent 0.16.27](https://github.com/rakshasa/rtorrent/releases/tag/v0.16.27),
  [upstream Docker wiki](https://github.com/rakshasa/rtorrent/wiki/Docker)
- [rqbit 9.1.0](https://github.com/ikatson/rqbit/releases/tag/v9.1.0),
  [upstream Docker instructions](https://github.com/ikatson/rqbit#docker)

## Workloads

| Workload | Payload | What is timed |
|---|---|---|
| Empty idle | No torrents | 15 s idle resource usage |
| Large download | 1 × 4 GiB, 1 MiB pieces | API add through verified client completion |
| Recheck | Existing 4 GiB | Forced hash check, with the checking state observed before completion |
| Upload | 4 GiB to each of two leechers | Both independent leechers finish, 8 GiB aggregate |
| Many files | 2,048 × 512 KiB, 256 KiB pieces | 1 GiB download and file management |
| Concurrent | 64 × 16 MiB, 256 KiB pieces | All 64 downloads finish, 1 GiB aggregate |
| Loaded idle | 64 complete torrents | 15 s idle resource usage |
| Rate limited | 1 GiB, 1 MiB pieces | Two seeds, each capped at 16 MiB/s |
| Catalog | 1,000 × 64 KiB, paused | Register all torrents, then 15 s idle memory |

All torrents use BEP 3/v1 metadata with `private=1`, a single local HTTP tracker,
and no web seeds. Payloads are deterministic SHAKE-256 bytes, with a distinct
seed for every file and 1 MiB block; they are physically written,
not sparse files. There is no compression/deduplication configured by this lab.
The tracker accepts only fixture hashes and private IPv4 peers. Runtime services
have only an `internal: true` Docker network. DHT, local discovery, PEX, and
port forwarding are disabled. Reference peers use TCP only, so the measured
transfers use plaintext TCP even when a client's default also permits uTP or
protocol encryption. Encryption is disabled at the reference peers so every
client uses the same wire protocol.

Two separate libtorrent 2.0.13 reference processes serve the fixtures. For upload
tests, two additional dedicated processes act as leechers with empty destination directories
and PEX disabled. The fixture seeders unload their torrents; only the tested
client remains a seed. A role-aware tracker permits discovery in both directions
but never returns one leecher to the other, even after one finishes downloading.
They cannot exchange data with each other. Their torrent piece hashes
verify uploaded bytes. Every client download also passes a separate Python
SHA-256 check against the generator's manifest, outside the timed interval.
Completion requires a seed-ready state for qBittorrent. If a disk write or rename
is still settling, verification retries for up to 30 seconds and records the
initial discrepancy, attempt count, and verification duration. Persistent
mismatches fail the run; they are never accepted as successful transfers.
Reference sessions bind outgoing connections to their lab interface explicitly.
Their accept backlog is raised from libtorrent's default of 5 to 2,048, with
2,000 connection/unchoke slots, to accommodate the concurrent-torrent burst.

Clients each receive 2 CPU cores of quota, 1,536 MiB of memory, no swap, and the
same file descriptor limit. Only one client runs at a time. Each reference peer
also receives 2 cores and 1,536 MiB. Queue/connection limits are raised to allow
the concurrent workload. General cache and disk algorithms stay at the image
defaults. Deluge includes its web process; rTorrent is its daemon without an
additional ruTorrent stack. This measures the selected deployable images and
their libraries, not just isolated language runtimes.
rqbit runs as its image's default root user: the pinned image's certificate
directory lacks traversal permission for non-root users. No extra processes
are added to work around this packaging issue.

Each workload gets a fresh client process, clean config, and newly created
destination files. Upload/recheck intentionally reuse the just-downloaded large
file. By default, three repetitions rotate client order. The source and Linux page caches
are not globally cleared; these are local, usually warm-cache results, not
cold-disk or WAN results. The rate-limited case caps application payload rates;
it does not simulate latency, packet loss, or a real internet path.
Client teardown is outside the measured interval and allows 10 seconds before
Docker terminates a process that has not exited; only this lab's disposable
files are involved. Shutdown durability and graceful-shutdown speed are not
tested.

## Measurements and artifacts

- `trials.json`: every elapsed time, throughput, CPU time, sampled memory peak,
  verification result, and reference-peer resource usage.
- `samples.jsonl` (archived as `samples.jsonl.gz`): resource time series, sampled roughly every 0.5 seconds plus
  collection overhead; actual monotonic timestamps are included.
- `environment.json`: Docker/VM capacity, architecture, kernel, image IDs,
  resource limits, and arguments.
- `*-effective-settings.json`: actual client settings/version responses.
- `complete.json`: written only after the requested suite finishes.
- `failure.txt`: retained if a trial fails; failed pilots are not valid results.

An upload with no verified payload progress for 120 seconds, or taking more than
600 seconds, is recorded as `status: timeout` with partial progress and resource
measurements. It gets no completed-payload throughput value. The suite continues
with the remaining cases, and `complete.json` explicitly lists any such timeouts.
Infrastructure and data-verification errors stop the run instead.

Throughput uses MiB/s (2²⁰ bytes/s). Download wall time includes adding torrents,
peer discovery, initial hashing/allocation, transfer, and completion reporting.
The report also includes a transfer rate between the first progress samples at
or above 10% and 90% completion, plus the first observed payload time. These help
separate startup delays from the active transfer. Progress is polled every
0.2 seconds, so the fastest small workloads have limited time resolution.
If an API's byte counter resets during initialization or hashing, the derived
startup/active-rate estimates are suppressed. Raw progress samples and the valid
completed-payload wall rate remain available.
CPU time is the cgroup
CPU counter delta; 100% means one fully occupied CPU core, with a 200% quota.
Recheck rates can exceed disk speed because the data is cached. rqbit has no
force-recheck API, so its recheck forgets the torrent and re-adds existing files
to force its initialization hash check.

Transmission 4.1 determines its source address by connecting a UDP socket to a
hardcoded external IP; the upstream code notes that this sends no packet.
Docker's internal network has no default route, so the lab adds only an on-link
`91.121.74.28/32` route inside the Transmission container before startup. This
requires `NET_ADMIN` in that container. The network remains internal, without a
default route or internet gateway. See the
[upstream probe implementation](https://github.com/transmission/transmission/blob/4.1.4/libtransmission/ip-cache.cc)
and `bench/transmission-init.sh`.

Memory is reported several ways to avoid hiding disk cache or mislabeling RSS:

- **Process RSS:** sum of RSS for all processes in the container; includes shared
  executable pages and resident mapped files, and can double count shared pages.
- **Anonymous memory:** cgroup anonymous resident allocation, useful for comparing
  heap/state costs; not total RSS.
- **Container total:** cgroup charged memory, including filesystem cache and kernel
  allocations; includes reclaimable cache and can reach the cap during writes.
- **Working set:** Docker-style `usage - inactive_file`; an accounting convention,
  not a guarantee that the rest cannot be reclaimed.
- **File cache:** cgroup charged file pages. Shared source/image cache pages may be
  charged elsewhere. Memory peaks are sampled and can miss short spikes.

RSS can exceed a container's charged-memory limit when resident mapped pages are
charged to another cgroup, for example after a separate verifier reads a shared
file. RSS and charged container memory should not be treated as interchangeable.

Reference peer CPU/quota counters help identify generator bottlenecks. A common
local throughput ceiling is a limitation of the lab, not evidence that the
clients have identical maximum performance. Results do not establish behavior
under hostile peers, thousands of active internet peers, HDD random I/O, VPNs,
encryption, v2/hybrid metadata, latency/loss, or long-term memory retention.
In each trial's metrics, `peer1`/`peer2` refer to the active reference processes:
the dedicated leechers for uploads and the seeders for other workloads.

## Fixture validation

After generating the fixtures:

```sh
docker compose --env-file images.env run --rm --no-deps \
  --entrypoint /lsiopy/bin/python3 peer1 /bench/test_fixtures.py
```

This checks canonical encoding, all 1,067 hashes/sizes/private/local tracker
invariants with libtorrent, and every piece hash/path of the 2,048-file fixture.

## Published run provenance

The published comparison combines the unaffected baseline cases, a complete
three-repeat qBittorrent rerun, and the remaining Deluge repetition. The baseline
stopped on an immediate qBittorrent filesystem verification mismatch; all 2,048
files matched after clean shutdown. Completion/recheck monitoring was tightened,
and every qBittorrent baseline case was replaced. See [REPORT.md](REPORT.md) for
the interpretation and limitations. Original records, including the failure,
remain in `results/runs/`; `results/comparison/selection.json` specifies the
selection rule. No fastest-run selection is performed.

To reproduce the published tables from the archived measurements:

```sh
python3 bench/assemble_results.py results/runs/baseline \
  results/runs/qbittorrent-corrected results/runs/deluge-final-repeat \
  results/reassembled
python3 bench/validate_results.py results/reassembled
python3 bench/summarize.py results/reassembled
```

Choose an unused destination. The assembly script reads compressed or plain
resource samples and preserves the raw measured times and resource counters.
Future uninterrupted full runs can be summarized and validated directly.
