# Executed torrent client comparison

Measured on **2026-11-02**, with aria2 added on **2026-11-03**. rqbit offered the strongest combination of throughput
and small application memory in this lab. qBittorrent had the fastest median
large-file download. Transmission used little application memory but completed
downloads more slowly. rTorrent used very little anonymous memory, with large
file mappings and a repeatable upload startup delay. Deluge had the largest
application memory footprint and highest CPU cost for the large download.
aria2 offered another small application footprint, with moderate bulk-transfer
rates and the slowest cached recheck in this suite.

The synthetic findings come from actual BitTorrent transfers: **180 accepted phases,
three repetitions per client, 270 GiB of payload**. All data and torrent metadata
were generated locally. The Compose runtime network was internal, with no public
torrents, internet trackers, magnets, or published ports.

## Ubuntu public download

**The main public experiment completed all 36 planned attempts: six fresh attempts for each of six clients. Thirty downloads finished within the 15-minute deadline and passed independent filesystem SHA-256 verification; six timed out.** It ran on 2026-11-03 from **19:36:00 to 22:08:00 UTC**. This is separate from the synthetic lab. The host used **1000baseT full duplex** Ethernet throughout: all 920 sanitized observations confirmed active gigabit media and primary IPv4/IPv6 routes through `en9`. This establishes the local link, not ISP capacity.

**Main findings.** rTorrent had the highest completed-download median, **41.09 MiB/s**, and completed 6/6. rqbit reached **35.43 MiB/s** and qBittorrent **31.71 MiB/s**, also 6/6. aria2 completed 5/6 at a conditional median of **32.38 MiB/s**, but its 9.65–84.99 MiB/s range and timeout show substantial variability. Transmission completed 5/6 at **14.52 MiB/s**; its timeout reached approximately 99.956% reported progress without completing. Deluge's native empty-interface configuration completed only 2/6, at **11.28 MiB/s**. Its loaded-download estimate therefore has only two observations; the separately registered interface follow-up below addresses that limitation without replacing these failures.

The source was the unmodified official [Ubuntu 26.04.1 live server AMD64 torrent](https://releases.ubuntu.com/26.04/ubuntu-26.04.1-live-server-amd64.iso.torrent): **2,927,861,760 bytes, 2,792.23 MiB (2.73 GiB)**, 256 KiB pieces, 11,169 pieces, two HTTPS tracker endpoints, and no web seeds. The [torrent provenance](ubuntu/source.json) records the metadata and official checksum source. Each completed rate divides this fixed payload by elapsed time from API submission through reported completion, including discovery, initialization, transfer, and final-piece delays. Daemon startup and configuration happen before the timer; independent SHA-256 verification happens afterward with the client stopped. MiB/s means binary megabytes per second; multiply by 8.388608 for decimal Mb/s.

**Design registered before measurement.** A seeded six-round Williams design placed every client once in each execution position and every directed adjacent client pair once within rounds. Cross-round transitions are not included in that balance. The [protocol](results/ubuntu-six-runs/protocol.json) fixes the complete order, six attempts per client, and a **900-second deadline with no early no-progress cutoff**. All slots were executed sequentially; no failed or slow attempt was replaced. Configuration, session/DHT state, and destination files were reset for every attempt. This is fresh application state; host/VM filesystem caches were not globally flushed. An already running, warmed-DHT client was not tested. A final piece arriving after the deadline would still count as a timeout here.

The same six pinned versions and native ARM64 Docker environment as the synthetic suite were used, with **2 CPU cores, 1,536 MiB charged memory, and no container swap**. Seventeen Python harness files were archived and hash-checked; the measurement code stayed fixed throughout the main experiment. Effective settings were separately recorded and hashed for every attempt. DHT and PEX were enabled, LAN discovery and automatic port forwarding disabled, with native TCP/uTP support where available. Five clients used a 100-peer per-torrent limit; rqbit retained its native peer policy. Aria2 retained its default disabled IPv6 DHT while IPv6 peer transport was enabled. Those native engine differences are part of this deployable-image comparison.

The public Docker network supported outgoing **IPv4 and IPv6**, with NAT and no forwarded incoming ports; control traffic used a separate internal network. No synthetic peers ran alongside the public experiment. Deluge's empty native `listen_interface` preference resolves to `0.0.0.0` in [Deluge 2.2.0's implementation](https://github.com/deluge-torrent/deluge/blob/deluge-2.2.0/deluge/core/preferencesmanager.py#L205-L223). An aggregate socket inspection during its second, failed attempt found IPv4 sockets and no IPv6 peer sockets. It changed no settings, but the brief Python helper may add a small amount of CPU/RSS to that failed attempt; the [observation record](results/ubuntu-six-runs/observations.json) discloses it. Completed-download resource summaries exclude that attempt. No peer addresses or IDs were retained.

**Statistics retain failures.** Throughput medians, IQRs, and ranges are conditional on verified completion. A failure has no complete-file rate, rather than an invented zero rate. Completion counts show all attempts; a separate deadline-penalized mean assigns every failure the full 900 seconds. Thus the chart's speed ranking and the penalized-time ranking answer different questions. A six-success sample still has a wide Wilson interval; these are descriptive results, with no significance test or universal capacity claim.

Six registered attempts per client, 36 total; a fixed 900-second deadline, without an early stall cutoff. Median, interquartile range (IQR), and full range describe completed, SHA-256 verified downloads. Every failure remains in the completion count and receives 900 seconds in the penalized mean. Inclusive quartiles use linear interpolation at rank (n−1)×p. Speed and duration medians are computed separately from per-attempt values.

| Client | Completed | Wilson 95% completion interval | Median MiB/s | IQR MiB/s | Range MiB/s | Median seconds | Mean penalized seconds |
|---|---:|---:|---:|---:|---:|---:|---:|
| qBittorrent | 6/6 | 61.0%–100.0% | 31.71 | 27.44–35.70 | 23.34–38.93 | 88.16 | 91.61 |
| Deluge | 2/6 | 9.7%–70.0% | 11.28 | 11.24–11.32 | 11.20–11.36 | 247.49 | 682.50 |
| Transmission | 5/6 | 43.6%–97.0% | 14.52 | 13.93–15.29 | 8.03–24.59 | 192.27 | 322.77 |
| rTorrent | 6/6 | 61.0%–100.0% | 41.09 | 38.38–52.60 | 38.17–58.95 | 68.25 | 63.34 |
| rqbit | 6/6 | 61.0%–100.0% | 35.43 | 34.39–36.39 | 29.76–37.83 | 78.85 | 80.55 |
| aria2 | 5/6 | 43.6%–97.0% | 32.38 | 27.16–63.18 | 9.65–84.99 | 86.23 | 242.55 |

**All-attempt resource costs, including failed/partial work.** Memory cells show the median of per-attempt sampled peaks / the largest sampled peak. Charged memory includes filesystem cache; RSS includes resident mappings; anonymous memory isolates resident allocations. These are different counters.

| Client | CPU core-s median (range) | Peak anonymous MiB, median / max | Peak RSS MiB, median / max | Peak charged MiB, median / max | Peak working MiB, median / max |
|---|---:|---:|---:|---:|---:|
| qBittorrent | 30.05 (29.02–46.05) | 39.36 / 97.45 | 73.36 / 160.53 | 1,536.04 / 1,536.62 | 89.14 / 138.90 |
| Deluge | 26.04 (24.23–132.79) | 83.61 / 130.16 | 157.32 / 1,504.23 | 103.76 / 1,537.56 | 90.26 / 1,420.68 |
| Transmission | 45.81 (30.38–62.30) | 43.25 / 49.79 | 58.38 / 64.65 | 1,536.60 / 1,537.13 | 107.72 / 139.36 |
| rTorrent | 32.39 (28.00–45.31) | 8.23 / 10.24 | 1,256.35 / 1,347.00 | 1,536.70 / 1,537.44 | 1,513.97 / 1,526.12 |
| rqbit | 35.71 (33.45–50.71) | 19.84 / 19.92 | 32.53 / 32.61 | 1,536.11 / 1,537.28 | 108.01 / 177.68 |
| aria2 | 26.14 (5.04–30.12) | 8.37 / 12.31 | 17.53 / 21.43 | 1,536.03 / 1,536.41 | 58.02 / 75.80 |

**Completed-download resource costs.** The following subset excludes failed attempts, whose resources may cover discovery or only a small part of the ISO. Use this subset for loaded-download comparisons. Cells again show median / maximum sampled peak; CPU is a median.

| Client | Verified downloads | CPU core-s | Peak anonymous MiB | Peak RSS MiB | Peak charged MiB | Peak working MiB |
|---|---:|---:|---:|---:|---:|---:|
| qBittorrent | 6 | 30.05 | 39.36 / 97.45 | 73.36 / 160.53 | 1,536.04 / 1,536.62 | 89.14 / 138.90 |
| Deluge | 2 | 123.83 | 122.42 / 130.16 | 1,498.72 / 1,504.23 | 1,537.03 / 1,537.56 | 1,311.69 / 1,420.68 |
| Transmission | 5 | 43.35 | 44.56 / 49.79 | 59.43 / 64.65 | 1,536.64 / 1,537.13 | 110.88 / 139.36 |
| rTorrent | 6 | 32.39 | 8.23 / 10.24 | 1,256.35 / 1,347.00 | 1,536.70 / 1,537.44 | 1,513.97 / 1,526.12 |
| rqbit | 6 | 35.71 | 19.84 / 19.92 | 32.53 / 32.61 | 1,536.11 / 1,537.28 | 108.01 / 177.68 |
| aria2 | 5 | 26.73 | 9.41 / 12.31 | 18.50 / 21.43 | 1,536.05 / 1,536.41 | 58.89 / 75.80 |

**Discovery and observation quality.** Startup/active rates are omitted for rqbit and rTorrent because their counters can include initialization or hash-scan work. A dash also denotes unavailable address-family counters (not captured for rqbit). Peer maxima are sampled address counts from native APIs, with different client semantics, not unique-peer totals or a normalized capacity measure. Sampling intervals are median / maximum seconds; resource peaks can miss brief spikes, especially during the longer gaps.

| Client | First payload s (valid n) | Active 10–90% MiB/s (valid n) | Max observed IPv4 peers | Max observed IPv6 peers | Resource interval s | Status interval s |
|---|---:|---:|---:|---:|---:|---:|
| qBittorrent | 3.39 (6) | 44.14 (6) | 98 | 12 | 1.123 / 5.766 | 0.202 / 0.250 |
| Deluge | 2.57 (2) | 12.38 (2) | 99 | 0 | 0.530 / 4.398 | 0.211 / 0.294 |
| Transmission | 31.28 (5) | 34.57 (5) | 100 | 15 | 0.528 / 15.242 | 0.204 / 1.955 |
| rTorrent | — (0) | — (0) | 42 | 23 | 0.525 / 0.559 | 0.204 / 0.429 |
| rqbit | — (0) | — (0) | — | — | 1.063 / 13.778 | 0.202 / 0.299 |
| aria2 | 6.77 (5) | 70.30 (5) | 18 | 9 | 0.528 / 0.565 | 0.208 / 0.741 |

**Every registered attempt, in execution order.** Network receive bytes include BitTorrent and control/protocol traffic. The complete-file rate is absent on failure. CPU and sampled memory peaks describe that attempt; the sample count makes uneven resource observation visible.

| Slot | Round | Client | Result | Seconds | MiB/s | Received MiB | CPU core-s | Peak anonymous MiB | Peak RSS MiB | Peak charged MiB | Samples |
|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1 | aria2 | ok | 86.23 | 32.38 | 2,842.27 | 27.09 | 6.03 | 15.25 | 1,536.00 | 167 |
| 2 | 1 | rqbit | ok | 80.58 | 34.65 | 3,245.21 | 45.32 | 19.86 | 32.54 | 1,536.13 | 35 |
| 3 | 1 | Transmission | ok | 200.48 | 13.93 | 3,035.83 | 51.77 | 37.30 | 53.16 | 1,536.55 | 223 |
| 4 | 1 | Deluge | ok | 249.22 | 11.20 | 2,989.81 | 132.79 | 130.16 | 1,493.22 | 1,537.56 | 261 |
| 5 | 1 | rTorrent | ok | 47.36 | 58.95 | 2,987.09 | 45.31 | 8.27 | 1,224.78 | 1,537.15 | 91 |
| 6 | 1 | qBittorrent | ok | 105.85 | 26.38 | 2,881.18 | 46.05 | 40.24 | 77.56 | 1,536.20 | 48 |
| 7 | 2 | rqbit | ok | 93.81 | 29.76 | 3,179.56 | 50.71 | 19.83 | 32.52 | 1,536.07 | 36 |
| 8 | 2 | Deluge | timeout | 900.08 | — | 30.71 | 26.71 | 83.80 | 170.68 | 117.40 | 1707 |
| 9 | 2 | aria2 | timeout | 900.15 | — | 40.81 | 5.04 | 5.64 | 14.70 | 42.49 | 1701 |
| 10 | 2 | qBittorrent | ok | 71.72 | 38.93 | 2,878.70 | 29.70 | 97.45 | 160.53 | 1,536.05 | 66 |
| 11 | 2 | Transmission | ok | 182.60 | 15.29 | 3,014.47 | 43.35 | 49.79 | 64.65 | 1,536.76 | 223 |
| 12 | 2 | rTorrent | ok | 72.71 | 38.40 | 2,941.80 | 34.50 | 8.64 | 1,225.43 | 1,536.84 | 139 |
| 13 | 3 | rTorrent | ok | 72.77 | 38.37 | 2,922.64 | 31.03 | 7.51 | 1,267.33 | 1,536.56 | 140 |
| 14 | 3 | Transmission | timeout | 900.16 | — | 3,005.46 | 62.30 | 41.94 | 57.34 | 1,536.45 | 1557 |
| 15 | 3 | qBittorrent | ok | 85.08 | 32.82 | 2,879.16 | 29.91 | 35.21 | 65.72 | 1,535.99 | 44 |
| 16 | 3 | aria2 | ok | 102.79 | 27.16 | 2,892.47 | 30.12 | 12.31 | 21.43 | 1,536.41 | 199 |
| 17 | 3 | Deluge | timeout | 900.03 | — | 3.58 | 25.36 | 81.64 | 142.41 | 88.54 | 1701 |
| 18 | 3 | rqbit | ok | 73.82 | 37.83 | 3,103.25 | 33.45 | 19.92 | 32.61 | 1,536.08 | 43 |
| 19 | 4 | Transmission | ok | 113.55 | 24.59 | 2,908.27 | 30.38 | 29.14 | 44.14 | 1,536.64 | 218 |
| 20 | 4 | aria2 | ok | 44.20 | 63.18 | 2,892.27 | 26.73 | 11.02 | 20.05 | 1,536.12 | 86 |
| 21 | 4 | rTorrent | ok | 63.78 | 43.78 | 2,883.56 | 33.75 | 10.24 | 1,347.00 | 1,537.44 | 123 |
| 22 | 4 | rqbit | ok | 76.61 | 36.45 | 3,228.88 | 35.79 | 19.52 | 32.21 | 1,536.04 | 32 |
| 23 | 4 | qBittorrent | ok | 91.25 | 30.60 | 2,871.34 | 30.19 | 37.49 | 67.32 | 1,536.03 | 43 |
| 24 | 4 | Deluge | ok | 245.77 | 11.36 | 3,045.96 | 114.86 | 114.68 | 1,504.23 | 1,536.50 | 178 |
| 25 | 5 | qBittorrent | ok | 119.62 | 23.34 | 2,895.69 | 36.44 | 47.09 | 77.56 | 1,536.62 | 73 |
| 26 | 5 | rTorrent | ok | 73.16 | 38.17 | 2,869.06 | 30.67 | 8.19 | 1,245.37 | 1,536.21 | 141 |
| 27 | 5 | Deluge | timeout | 900.19 | — | 3.57 | 24.38 | 83.43 | 143.97 | 90.12 | 1698 |
| 28 | 5 | Transmission | ok | 347.72 | 8.03 | 3,030.92 | 48.28 | 44.56 | 59.43 | 1,536.54 | 498 |
| 29 | 5 | rqbit | ok | 81.39 | 34.31 | 3,197.98 | 35.64 | 19.87 | 32.55 | 1,536.20 | 36 |
| 30 | 5 | aria2 | ok | 32.85 | 84.99 | 2,842.10 | 22.51 | 7.33 | 16.55 | 1,536.05 | 64 |
| 31 | 6 | Deluge | timeout | 900.21 | — | 3.59 | 24.23 | 82.16 | 142.56 | 88.82 | 1699 |
| 32 | 6 | qBittorrent | ok | 76.16 | 36.66 | 2,878.53 | 29.02 | 38.48 | 69.16 | 1,535.98 | 51 |
| 33 | 6 | rqbit | ok | 77.12 | 36.20 | 3,099.69 | 33.55 | 19.68 | 32.37 | 1,537.28 | 26 |
| 34 | 6 | rTorrent | ok | 50.27 | 55.55 | 2,895.48 | 28.00 | 6.48 | 1,329.41 | 1,535.96 | 98 |
| 35 | 6 | aria2 | ok | 289.25 | 9.65 | 2,864.94 | 25.55 | 9.41 | 18.50 | 1,535.99 | 550 |
| 36 | 6 | Transmission | ok | 192.27 | 14.52 | 2,963.88 | 42.67 | 45.30 | 61.07 | 1,537.13 | 243 |

Audit: 36 attempts; 30 independent SHA-256 checks; 14,238 resource samples; 920 sanitized Ethernet/route observations. No ISO retained.

This experiment describes cold client state on this host, network, and swarm during the recorded window. It does not estimate universal client capacity. Six trials still have substantial uncertainty; even 6/6 completions gives a Wilson lower bound of about 61%, under a binomial model. Swarm and temporal dependence further limit that model. There are no significance claims.


**What the memory figures mean.** Among completed downloads, rTorrent's median peak anonymous allocation was only **8.23 MiB**, but its median peak RSS was **1,256.35 MiB** and working usage **1,513.97 MiB** because file mappings/cache are substantial. It cannot be described as an 8 MiB-RAM client. rqbit combined a 19.84 MiB median anonymous peak with 32.53 MiB RSS; aria2's corresponding values were 9.41 and 18.50 MiB across five completions. qBittorrent reached 39.36/73.36 MiB and Transmission 44.56/59.43 MiB. Deluge's two completions reached 122.42/1,498.72 MiB. Anonymous memory excludes file-backed pages; RSS sums resident process mappings and may double-count shared pages. Charged memory includes filesystem cache; working usage subtracts inactive file pages. These counters describe different costs, not minimum RAM requirements.

Every completed transfer approached the configured 1,536 MiB charged limit, mostly through filesystem cache. Small sampled overshoots are allowed temporarily by the [Linux cgroup memory controller](https://docs.kernel.org/admin-guide/cgroup-v2.html#memory-interface-files). No accepted main attempt was OOM-killed. CPU core-seconds are cumulative cgroup CPU usage, not elapsed seconds or CPU percentage; idle timeouts can consume less CPU than a complete transfer. That is why both all-attempt and completed-download resource tables are included.

**Observation limits.** Resource polling targeted 0.5 seconds, status polling 0.2 seconds, and optional discovery polling 15 seconds. Actual resource gaps differed by client: the largest was **15.242 seconds**, and rqbit's was 13.778 seconds. The cadence table makes this visible. Sampled peaks are lower bounds on transient peaks; small memory differences should not be treated as precise rankings. Cumulative CPU and network deltas do not lose work between samples. All peak/median resource values and cumulative deltas were independently recomputed from the 14,238 raw samples. No optional diagnostic RPC errors occurred in the main experiment. Startup/active-window diagnostics are suppressed for rTorrent and rqbit because initialization/hash-scan counters can resemble transferred payload. Their complete-file wall rates, network RX, and filesystem verification remain valid.

**Disk handling and integrity.** The 30 verified main downloads total **81.80 GiB** of ISO payload, demonstrating repeated actual transfers rather than reuse of a preexisting ISO. Each successful attempt's measured network receive count exceeds the full payload. Each attempt deleted the ISO and sidecars and recorded an empty scratch directory: 36/36 cleanups. The clients share one scratch volume, so at most one 2.73 GiB ISO payload is present at a time. The project removes its containers and volumes on exit; **no ISO is retained**. This is a payload-retention limit, not a cap on Docker's overall image/VM disk allocation. The independent expected SHA-256 from [Ubuntu's SHA256SUMS](https://releases.ubuntu.com/26.04/SHA256SUMS) is `cc8a95cde20f6ced61a322420de00f10cc3c90ced545daa46cb9c1a117f1d927`.

**Interpretation.** This is a real public-swarm experiment on one connection in one time window, with controlled image versions, resource limits, payload, cold application state, and balanced order. Peer availability, tracker responses, DHT bootstrap, endgame behavior, and ISP conditions remain uncontrolled. The balance mitigates time/order effects; it cannot eliminate them or establish independent, stationary observations. The [reported Ubuntu IPv4 tracker problem](https://github.com/canonical/ubuntu.com/issues/15735) is relevant context, but does not prove the cause of any individual failure. The earlier rTorrent/aria2 IPv4-only failures do not demonstrate low transfer capacity: both downloaded the complete ISO in this dual-stack main experiment. Nor does aria2's fastest 84.99 MiB/s observation establish a stable maximum. These findings describe the tested cold-start deployment, not an already connected client or every network.

**Separate Deluge interface follow-up.** The [conditional follow-up plan](results/ubuntu-six-runs/followup-plan.json) was recorded at 21:10 UTC, before the main experiment finished. Its trigger was fewer than three Deluge completions in the fixed six main attempts; the [decision](results/ubuntu-six-runs/followup-decision.json) records the actual 2/6. It fixes another six attempts under the same deadline and quotas, changing one client preference: `listen_interface` binds to the Linux interface carrying the default outgoing route. A paused, untimed preflight verifies IPv4 and IPv6 TCP/UDP sockets before transfers. Binding that interface changes both interface selection and address-family availability; this is not an isolated proof of IPv6 causality. It runs later and remains a separate condition, never pooled into or substituted for the native 36 attempts.

The first interface follow-up exposed an observer defect: optional discovery RPCs timed out and blocked synchronous completion polling. Its recorded completed downloads and interrupted attempt are preserved as an [excluded diagnostic run](results/runs/ubuntu-deluge-interface-observer-diagnostic/invalidated.json), with original samples and traceback. Before starting a new fixed six-attempt series, the observer was amended to skip these optional RPCs for this profile. Basic status polling, resource collection, the fixed deadline, and client settings were otherwise retained. Discovery RPC suppression affects observation only; it does not disable peer discovery. The [follow-up study record](results/ubuntu-deluge-ipv6/study.json) records this amendment in advance. The audit rejects optional RPC errors in any performance cohort. The main experiment had zero such errors and is unchanged.

**Follow-up findings: six more verified downloads, reported separately.** This series ran from **22:18:30 to 22:36:26 UTC** on 2026-11-03. Deluge completed **6/6**, with **17.31 MiB/s median**, **15.60–19.40 MiB/s IQR**, and **11.28–20.78 MiB/s range**. Median completion time was 161.99 seconds. Median CPU cost was 70.39 core-seconds; median sampled anonymous/RSS peaks were **155.56 / 1,493.55 MiB**. These are loaded measurements across six full transfers, alongside the original native-profile results rather than replacing them.

The later interface profile completed more consistently in this window, but the changed binding, later swarm conditions, and observer amendment prevent attributing the difference solely to IPv6. The untimed preflight proves socket availability, not which address family supplied the payload. Docker renamed the outgoing interface between fresh starts (`eth0`/`eth1`); the archived init script detects the default route each time, and every effective setting records that selected interface. The [interface observation](results/ubuntu-deluge-ipv6/observations.json) explains why the preflight's literal interface name is not held fixed.

Six registered attempts per client, 6 total; a fixed 900-second deadline, without an early stall cutoff. Median, interquartile range (IQR), and full range describe completed, SHA-256 verified downloads. Every failure remains in the completion count and receives 900 seconds in the penalized mean. Inclusive quartiles use linear interpolation at rank (n−1)×p. Speed and duration medians are computed separately from per-attempt values.

| Client | Completed | Wilson 95% completion interval | Median MiB/s | IQR MiB/s | Range MiB/s | Median seconds | Mean penalized seconds |
|---|---:|---:|---:|---:|---:|---:|---:|
| Deluge interface | 6/6 | 61.0%–100.0% | 17.31 | 15.60–19.40 | 11.28–20.78 | 161.99 | 171.49 |

**Completed-download resource costs.** The following subset excludes failed attempts, whose resources may cover discovery or only a small part of the ISO. Use this subset for loaded-download comparisons. Cells again show median / maximum sampled peak; CPU is a median.

| Client | Verified downloads | CPU core-s | Peak anonymous MiB | Peak RSS MiB | Peak charged MiB | Peak working MiB |
|---|---:|---:|---:|---:|---:|---:|
| Deluge interface | 6 | 70.39 | 155.56 / 179.88 | 1,493.55 / 1,520.41 | 1,537.09 / 1,540.48 | 1,396.60 / 1,435.78 |

**Follow-up observation quality.** Peer-family/discovery counters were intentionally not collected; a dash is not zero IPv6 traffic. Startup/active diagnostics below use basic status polling. Resource intervals are median / maximum, and peaks remain sampled lower bounds.

| Client | First payload s (valid n) | Active 10–90% MiB/s (valid n) | Max observed IPv4 peers | Max observed IPv6 peers | Resource interval s | Status interval s |
|---|---:|---:|---:|---:|---:|---:|
| Deluge interface | 5.04 (6) | 19.64 (6) | — | — | 0.528 / 8.075 | 0.204 / 0.255 |

**Every registered attempt, in execution order.** Network receive bytes include BitTorrent and control/protocol traffic. The complete-file rate is absent on failure. CPU and sampled memory peaks describe that attempt; the sample count makes uneven resource observation visible.

| Slot | Round | Client | Result | Seconds | MiB/s | Received MiB | CPU core-s | Peak anonymous MiB | Peak RSS MiB | Peak charged MiB | Samples |
|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1 | Deluge interface | ok | 181.33 | 15.40 | 3,033.69 | 85.76 | 136.95 | 1,445.54 | 1,537.11 | 318 |
| 2 | 2 | Deluge interface | ok | 141.62 | 19.72 | 2,947.97 | 63.81 | 160.29 | 1,452.12 | 1,536.94 | 135 |
| 3 | 3 | Deluge interface | ok | 134.36 | 20.78 | 2,935.09 | 65.05 | 158.96 | 1,520.41 | 1,536.01 | 87 |
| 4 | 4 | Deluge interface | ok | 247.65 | 11.28 | 3,030.57 | 98.23 | 145.07 | 1,507.91 | 1,537.07 | 297 |
| 5 | 5 | Deluge interface | ok | 151.46 | 18.44 | 2,960.06 | 61.21 | 152.15 | 1,507.68 | 1,540.48 | 152 |
| 6 | 6 | Deluge interface | ok | 172.52 | 16.18 | 3,001.49 | 75.74 | 179.88 | 1,479.43 | 1,537.15 | 291 |

Audit: 6 attempts; 6 independent SHA-256 checks; 1,280 resource samples; 112 sanitized Ethernet/route observations. No ISO retained.

This experiment describes cold client state on this host, network, and swarm during the recorded window. It does not estimate universal client capacity. Six trials still have substantial uncertainty; even 6/6 completions gives a Wilson lower bound of about 61%, under a binomial model. Swarm and temporal dependence further limit that model. There are no significance claims.

The [separate follow-up audit](results/ubuntu-deluge-ipv6/validation.json), [analysis](results/ubuntu-deluge-ipv6/analysis.json), [every follow-up observation CSV](results/ubuntu-deluge-ipv6/attempts.csv), [trial records](results/ubuntu-deluge-ipv6/trials.json), and [compressed resource samples](results/ubuntu-deluge-ipv6/samples.jsonl.gz) retain this condition's evidence. All 112 follow-up Ethernet observations passed; all six payloads were deleted and project volumes removed. Across the main experiment and this valid follow-up, **42 attempts produced 36 independently verified downloads, 98.16 GiB of verified ISO payload, and 15,518 resource samples**. Excluded diagnostic runs and older pilots are additional evidence, outside those totals.


**Evidence and reproduction.** The [full analysis](results/ubuntu-six-runs/analysis.json), [all observations CSV](results/ubuntu-six-runs/attempts.csv), [trial records](results/ubuntu-six-runs/trials.json), [compressed resource time series](results/ubuntu-six-runs/samples.jsonl.gz), [Ethernet monitor](results/ubuntu-six-runs/host-link.jsonl), [frozen harness](results/ubuntu-six-runs/harness/ubuntu_run.py), and [validation audit](results/ubuntu-six-runs/validation.json) retain the measurements and hashes. The audit verifies the planned slots/order, payload, SHA-256 checks, fresh effective settings, image/resource conditions, all resource aggregates, cleanup, and monitor coverage. See the [README reproduction commands](README.md#public-ubuntu-fresh-downloads), including the separate link monitor. The public workload, torrent metadata, and harness are reproducible; the same Internet swarm conditions and numerical speeds are not.

**Historical pilots, excluded from these estimates.** The earlier [IPv4-only one-attempt snapshot](results/ubuntu-public/summary.csv), [selection record](results/ubuntu-public/selection.json), [initial interrupted diagnostic](results/runs/ubuntu-initial-diagnostic/interrupted.json), and [two-client dual-stack smoke test](results/runs/ubuntu-dualstack-pilot/trials.json) remain available. They used different setup/stopping rules and are not repetitions of the registered main experiment. Keeping them separate avoids choosing whichever attempt looked fastest. The synthetic comparison below remains its original three repetitions per client.

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
charged-memory limit, and no swap**. Only one client ran at a time. In the synthetic suite, two independent
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

The synthetic suite is a local TCP benchmark with generated private v1 torrents, mostly warm
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
