# Executed torrent client comparison

Measured on **2026-11-02**, with aria2 added on **2026-11-03**. rqbit offered the strongest combination of throughput
and small application memory in this lab. qBittorrent had the fastest median
large-file download. Transmission used little application memory but completed
downloads more slowly. rTorrent used very little anonymous memory, with large
file mappings and a repeatable upload startup delay. Deluge had the largest
application memory footprint and highest CPU cost for the large download.
aria2 offered another small application footprint, with moderate bulk-transfer
rates and the slowest cached recheck in this suite.

These findings come from actual BitTorrent transfers: **180 accepted phases,
three repetitions per client, 270 GiB of payload**. All data and torrent metadata
were generated locally. The Compose runtime network was internal, with no public
torrents, internet trackers, magnets, or published ports.

## Versions and conditions

| Client | Tested stable version | Distribution |
|---|---|---|
| qBittorrent | 5.3.0; libtorrent 2.1.2 | Upstream official image |
| Deluge | 2.2.0; libtorrent 2.0.13 | LinuxServer community image |
| Transmission | 4.1.4 | LinuxServer community image |
| rTorrent | 0.16.27; Rakshasa libtorrent 0.16.27 | Checksum-verified upstream source build |
| rqbit | 9.1.0 | Upstream author's image |
| aria2 | 1.37.0; Alpine package 1.37.0-r2 | Minimal local image with locked distribution packages |

Stable releases were checked against upstream sources and installed binaries.
Prebuilt images are pinned by digest. rTorrent's base, source checksums, and APK
versions are pinned; a fresh locked build reproduced both measured binary
hashes. [Image references and primary sources](README.md#images-and-provenance)
document the choices where an upstream image was unavailable.
aria2's base and runtime package versions are pinned too; its executable hash,
package inventory, and build-version output are retained in `aria2/`.

The host was Docker Desktop 29.9.2, Linuxkit 7.0.14, native ARM64, with 8 virtual
CPUs and 7.75 GiB of VM memory. Each client had a **2-core quota, 1,536 MiB
charged-memory limit, and no swap**. Only one client ran at a time. Two independent
reference seeders supplied downloads; two separate leechers received uploads.
Each reference process also had two cores and 1,536 MiB. Data lived in Linux
Docker volumes. Deluge includes its normal web process; rTorrent has no ruTorrent
front end. This compares the selected deployable images and their libraries.

## Transfer results

**Median MiB/s across three repetitions**, from API submission through client
completion. This includes discovery, initialization, transfer, and completion
reporting. Downloads then underwent independent filesystem SHA-256 verification
outside the timer. Uploads count 8 GiB total: 4 GiB received and piece-verified
by each of two leechers.

| Client | 4 GiB download | 2,048 files, 1 GiB | 64 torrents, 1 GiB | 32 MiB/s capped | Two-peer upload |
|---|---:|---:|---:|---:|---:|
| qBittorrent | **399.1** | 250.3 | 179.5 | 29.9 | 367.4 |
| Deluge | 171.1 | 96.5 | 61.8 | 26.0 | 337.1 |
| Transmission | 91.2 | 50.8 | 47.1 | 23.2 | 242.6 |
| rTorrent | 257.2 | 257.4 | 66.9 | 30.7 | 96.0 |
| rqbit | 352.4 | **349.4** | **410.3** | **31.5** | **390.3** |
| aria2 | 183.6 | 133.9 | 207.4 | 30.0 | 218.2 |

rqbit led the many-file and concurrent medians. Its upload median also led, but
the upload ranges overlap qBittorrent and Deluge. qBittorrent's large downloads
took 10.18–11.69 seconds, versus rqbit's 11.42–12.15 seconds. Those close results
should be read with the collection-order limitation below.

aria2's large-download rate ranged from 144.4–193.5 MiB/s and its upload rate
from 200.9–289.3 MiB/s. Its large-download median sits between rTorrent and
Deluge, with overlapping ranges against Deluge. Its concurrent median exceeded
qBittorrent's, but those ranges also overlap and aria2 was measured a day later.

Concurrency was variable. The 64-torrent rates ranged from **99.6–247.4** MiB/s
for qBittorrent, **39.4–64.8** for Deluge, **19.8–72.9** for Transmission,
**37.0–395.2** for rTorrent, **273.1–515.6** for rqbit, and **70.7–214.9** for aria2. Three repetitions do
not support tight confidence intervals or a universal concurrency ranking.

rTorrent's upload took 84.93–88.18 seconds, with first verified payload at
60.43–61.22 seconds. Once transferring, its median 10–90% rate was **337.5
MiB/s**. Its poor overall upload rate here is largely a startup effect; the
exact cause was not established. Transmission's upload similarly improved from
242.6 MiB/s overall to 367.3 MiB/s in the active window.

Among the five clients with retained capped-transfer diagnostics, active-window
medians were approximately **31.8–32.1 MiB/s**. rTorrent's diagnostic was
suppressed because its progress counter reset. Overall rates differ mainly
because a roughly 32-second transfer magnifies discovery/startup costs. The
case caps the seeders' payload rate; it does not emulate WAN latency or packet
loss.

Some API progress counters reset during initialization/hash checking. Their
startup/active-rate diagnostics are suppressed, including rqbit's large-download
diagnostics and rTorrent's large/many-file/capped diagnostics. Raw samples remain
available. Completed-payload wall rates do not depend on those counters' slope.

## Memory and CPU

Memory below is **MiB**. Idle figures are medians of each repetition's sampled
median; peaks are the highest sample across all workloads and repetitions.

| Client | Empty idle RSS | 1,000 paused RSS | Peak anonymous memory | Peak summed process RSS |
|---|---:|---:|---:|---:|
| qBittorrent | 33.7 | 52.1 | 131.8 | 158.9 |
| Deluge | 138.8 | 180.2 | 222.2 | 3,340.8 |
| Transmission | 16.1 | 25.3 | 67.0 | 81.0 |
| rTorrent | 13.0 | 30.8 | 18.7 | 1,429.2 |
| rqbit | **9.6** | **17.1** | **12.3** | **23.7** |
| aria2 | 12.3 | 26.6 | 18.2 | 26.7 |

Anonymous memory helps distinguish application state from resident file
mappings. At 1,000 paused torrents, median anonymous allocations were 22.1 MiB
for qBittorrent, 119.5 for Deluge, 11.2 for Transmission, 18.7 for rTorrent,
5.8 for rqbit, and 18.2 for aria2. rqbit's small footprint persisted through this metadata load.
Deluge's web/daemon processes contribute to its higher baseline.

**RSS is not a minimum-RAM requirement.** It includes shared and mapped file
pages. Deluge's largest RSS sample occurred during rechecking; rTorrent's during
the large download. Shared file pages may be charged to another cgroup after a
verifier or peer reads them, so process RSS can exceed the container's charged
memory cap. Summed RSS can also double count shared pages. All clients approached
the roughly 1.5 GiB charged-memory cap during data-heavy phases, largely through
filesystem cache. The raw records retain total, anonymous, file-cache, and
Docker-style working-set counters separately. No accepted client was OOM-killed.

| Client | Large download CPU, core-s | Upload CPU, core-s | 4 GiB recheck, s | Register 1,000 paused, s |
|---|---:|---:|---:|---:|
| qBittorrent | 11.89 | 19.15 | 4.08 | 1.34 |
| Deluge | 36.09 | 27.40 | 3.65 | 2.38 |
| Transmission | 9.42 | 11.50 | 2.54 | 0.43 |
| rTorrent | 12.70 | 10.75 | 2.74 | 0.91 |
| rqbit | 16.92 | 19.75 | 2.49 | 1.40 |
| aria2 | 18.05 | 14.33 | 12.34 | 0.44 |

CPU values are median cgroup CPU consumption, not elapsed time: two busy cores
for one second consume two core-seconds. Lower CPU can accompany slower
transfers. Deluge's large-download CPU cost was about three times qBittorrent's.
The cached rechecks measure hashing plus API/state transitions. rqbit has no
force-recheck endpoint, so it forgets and re-adds existing files to invoke its
initialization hash check. aria2 similarly removes and re-adds the existing file
with `check-integrity=true`, after discarding its completion sidecar. Its
median recheck took 12.34 seconds, versus 2.49–4.08 seconds for the other clients.
Its default 16 MiB disk cache, `prealloc` allocation, disabled mmap, and 100-file
open-file cache were retained. Every accepted recheck visibly entered checking.
Catalog timings include the client's API and initialization behavior, not just
internal insertion speed. Fifteen-second idle windows do not test memory leaks.

## Validation and collection history

The [automated audit](results/comparison/validation.json) confirms 72 downloaded
workloads, 38,052 filesystem file checks, 18 observed rechecks, and 36 complete
upload receivers. Selected payload totals are **126 GiB downloaded and 144 GiB
uploaded**. Each client's measured network RX/TX exceeds its respective complete
payload. Upload leechers recorded zero uploaded payload, zero failed hash bytes,
and full received payloads. The tracker excludes sibling leechers from each
other's discovery even after completion. There were no accepted timeouts.

The first long run stopped when qBittorrent reported completion but immediate
filesystem verification found a mismatch. After clean shutdown, all 2,048 files
matched their expected hashes. This is consistent with deferred disk visibility;
the exact cause was not established and no persistent corruption was observed.
The harness now requires qBittorrent's seed-ready state, retries and discloses
transient verification failures, and fails persistent mismatches. Recheck
monitoring also now requires observing checking rather than inferring work from
CPU usage. **Every baseline qBittorrent case was replaced with three complete
new repetitions**, all of which passed verification on the first attempt.
The final Deluge repetition was completed separately. Unaffected baseline cases
were retained without choosing the fastest results.

aria2 contributed 30 phases and 45 GiB of payload in a separate three-repeat
extension. All 12 downloads passed independent SHA-256 verification on the first
attempt; all six upload receivers received the complete payload, uploaded zero
bytes to sibling receivers, and reported zero failed hash bytes. An initial
integration attempt stopped because the adapter expected `removed` after stopping
an already complete seed; aria2 instead reports the terminal state `complete`.
The adapter was corrected and all three full repetitions were restarted. No
measurements from that initial attempt were included.

The baseline rotated client order; corrective passes occurred later. System
drift and cache state can therefore affect close comparisons. Source runs,
the original failure, a post-failure diagnostic, and an explicit
[selection rule](results/comparison/selection.json) are retained. This was not
one uninterrupted 180-phase run. aria2 ran after a Docker Desktop restart on the
following day, with matching recorded CPU/memory capacity, kernel, engine version,
resource limits, and fixture manifest. Its cases were not interleaved with the
original five clients, so cache state and system drift may affect close rankings.
Ambiguous progress diagnostics were recalculated
from the original samples; wall times and resource counters were preserved.

## Scope and reproduction

This is a local TCP benchmark with generated private v1 torrents, mostly warm
Linux caches, two reference peers, and fixed resource limits. It establishes
observed performance for these images and workloads. It does not establish
maximum throughput independent of reference CPU/storage limits, cold HDD
behavior, encrypted/VPN transfers, internet peer diversity, v2 metadata,
latency/loss tolerance, or long-term memory use. Reference-peer CPU, throttling,
network, and block-I/O counters are retained to inspect lab bottlenecks.

Run `./run.sh --output my-run --repeats 3`, then
`python3 bench/summarize.py results/my-run` and
`python3 bench/validate_results.py results/my-run`.
The [README](README.md) contains setup, isolation details, complete methodology,
and commands to reconstruct the published selection from archived evidence.
All 60 client/workload groups, variation, CPU, memory, and valid active-window
rates are in [SUMMARY.md](results/comparison/SUMMARY.md),
[summary.csv](results/comparison/summary.csv), and
[trials.json](results/comparison/trials.json).
