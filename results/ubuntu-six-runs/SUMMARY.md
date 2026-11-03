# Repeated public Ubuntu fresh-download experiment

Six registered attempts per client, 36 total; a fixed 900-second deadline, without an early stall cutoff. Median, interquartile range (IQR), and full range describe completed, SHA-256 verified downloads. Every failure remains in the completion count and receives 900 seconds in the penalized mean. Inclusive quartiles use linear interpolation at rank (n−1)×p. Speed and duration medians are computed separately from per-attempt values.

| Client | Completed | Wilson 95% completion interval | Median MiB/s | IQR MiB/s | Range MiB/s | Median seconds | Mean penalized seconds |
|---|---:|---:|---:|---:|---:|---:|---:|
| qbittorrent | 6/6 | 61.0%–100.0% | 31.71 | 27.44–35.70 | 23.34–38.93 | 88.16 | 91.61 |
| deluge | 2/6 | 9.7%–70.0% | 11.28 | 11.24–11.32 | 11.20–11.36 | 247.49 | 682.50 |
| transmission | 5/6 | 43.6%–97.0% | 14.52 | 13.93–15.29 | 8.03–24.59 | 192.27 | 322.77 |
| rtorrent | 6/6 | 61.0%–100.0% | 41.09 | 38.38–52.60 | 38.17–58.95 | 68.25 | 63.34 |
| rqbit | 6/6 | 61.0%–100.0% | 35.43 | 34.39–36.39 | 29.76–37.83 | 78.85 | 80.55 |
| aria2 | 5/6 | 43.6%–97.0% | 32.38 | 27.16–63.18 | 9.65–84.99 | 86.23 | 242.55 |

**All-attempt resource costs, including failed/partial work.** Memory cells show the median of per-attempt sampled peaks / the largest sampled peak. Charged memory includes filesystem cache; RSS includes resident mappings; anonymous memory isolates resident allocations. These are different counters.

| Client | CPU core-s median (range) | Peak anonymous MiB, median / max | Peak RSS MiB, median / max | Peak charged MiB, median / max | Peak working MiB, median / max |
|---|---:|---:|---:|---:|---:|
| qbittorrent | 30.05 (29.02–46.05) | 39.36 / 97.45 | 73.36 / 160.53 | 1,536.04 / 1,536.62 | 89.14 / 138.90 |
| deluge | 26.04 (24.23–132.79) | 83.61 / 130.16 | 157.32 / 1,504.23 | 103.76 / 1,537.56 | 90.26 / 1,420.68 |
| transmission | 45.81 (30.38–62.30) | 43.25 / 49.79 | 58.38 / 64.65 | 1,536.60 / 1,537.13 | 107.72 / 139.36 |
| rtorrent | 32.39 (28.00–45.31) | 8.23 / 10.24 | 1,256.35 / 1,347.00 | 1,536.70 / 1,537.44 | 1,513.97 / 1,526.12 |
| rqbit | 35.71 (33.45–50.71) | 19.84 / 19.92 | 32.53 / 32.61 | 1,536.11 / 1,537.28 | 108.01 / 177.68 |
| aria2 | 26.14 (5.04–30.12) | 8.37 / 12.31 | 17.53 / 21.43 | 1,536.03 / 1,536.41 | 58.02 / 75.80 |

**Completed-download resource costs.** The following subset excludes failed attempts, whose resources may cover discovery or only a small part of the ISO. Use this subset for loaded-download comparisons. Cells again show median / maximum sampled peak; CPU is a median.

| Client | Verified downloads | CPU core-s | Peak anonymous MiB | Peak RSS MiB | Peak charged MiB | Peak working MiB |
|---|---:|---:|---:|---:|---:|---:|
| qbittorrent | 6 | 30.05 | 39.36 / 97.45 | 73.36 / 160.53 | 1,536.04 / 1,536.62 | 89.14 / 138.90 |
| deluge | 2 | 123.83 | 122.42 / 130.16 | 1,498.72 / 1,504.23 | 1,537.03 / 1,537.56 | 1,311.69 / 1,420.68 |
| transmission | 5 | 43.35 | 44.56 / 49.79 | 59.43 / 64.65 | 1,536.64 / 1,537.13 | 110.88 / 139.36 |
| rtorrent | 6 | 32.39 | 8.23 / 10.24 | 1,256.35 / 1,347.00 | 1,536.70 / 1,537.44 | 1,513.97 / 1,526.12 |
| rqbit | 6 | 35.71 | 19.84 / 19.92 | 32.53 / 32.61 | 1,536.11 / 1,537.28 | 108.01 / 177.68 |
| aria2 | 5 | 26.73 | 9.41 / 12.31 | 18.50 / 21.43 | 1,536.05 / 1,536.41 | 58.89 / 75.80 |

**Discovery and observation quality.** Startup/active rates are omitted for rqbit and rTorrent because their counters can include initialization or hash-scan work. A dash also denotes unavailable address-family counters (not captured for rqbit). Peer maxima are sampled address counts from native APIs, with different client semantics, not unique-peer totals or a normalized capacity measure. Sampling intervals are median / maximum seconds; resource peaks can miss brief spikes, especially during the longer gaps.

| Client | First payload s (valid n) | Active 10–90% MiB/s (valid n) | Max observed IPv4 peers | Max observed IPv6 peers | Resource interval s | Status interval s |
|---|---:|---:|---:|---:|---:|---:|
| qbittorrent | 3.39 (6) | 44.14 (6) | 98 | 12 | 1.123 / 5.766 | 0.202 / 0.250 |
| deluge | 2.57 (2) | 12.38 (2) | 99 | 0 | 0.530 / 4.398 | 0.211 / 0.294 |
| transmission | 31.28 (5) | 34.57 (5) | 100 | 15 | 0.528 / 15.242 | 0.204 / 1.955 |
| rtorrent | — (0) | — (0) | 42 | 23 | 0.525 / 0.559 | 0.204 / 0.429 |
| rqbit | — (0) | — (0) | — | — | 1.063 / 13.778 | 0.202 / 0.299 |
| aria2 | 6.77 (5) | 70.30 (5) | 18 | 9 | 0.528 / 0.565 | 0.208 / 0.741 |

**Every registered attempt, in execution order.** Network receive bytes include BitTorrent and control/protocol traffic. The complete-file rate is absent on failure. CPU and sampled memory peaks describe that attempt; the sample count makes uneven resource observation visible.

| Slot | Round | Client | Result | Seconds | MiB/s | Received MiB | CPU core-s | Peak anonymous MiB | Peak RSS MiB | Peak charged MiB | Samples |
|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1 | aria2 | ok | 86.23 | 32.38 | 2,842.27 | 27.09 | 6.03 | 15.25 | 1,536.00 | 167 |
| 2 | 1 | rqbit | ok | 80.58 | 34.65 | 3,245.21 | 45.32 | 19.86 | 32.54 | 1,536.13 | 35 |
| 3 | 1 | transmission | ok | 200.48 | 13.93 | 3,035.83 | 51.77 | 37.30 | 53.16 | 1,536.55 | 223 |
| 4 | 1 | deluge | ok | 249.22 | 11.20 | 2,989.81 | 132.79 | 130.16 | 1,493.22 | 1,537.56 | 261 |
| 5 | 1 | rtorrent | ok | 47.36 | 58.95 | 2,987.09 | 45.31 | 8.27 | 1,224.78 | 1,537.15 | 91 |
| 6 | 1 | qbittorrent | ok | 105.85 | 26.38 | 2,881.18 | 46.05 | 40.24 | 77.56 | 1,536.20 | 48 |
| 7 | 2 | rqbit | ok | 93.81 | 29.76 | 3,179.56 | 50.71 | 19.83 | 32.52 | 1,536.07 | 36 |
| 8 | 2 | deluge | timeout | 900.08 | — | 30.71 | 26.71 | 83.80 | 170.68 | 117.40 | 1707 |
| 9 | 2 | aria2 | timeout | 900.15 | — | 40.81 | 5.04 | 5.64 | 14.70 | 42.49 | 1701 |
| 10 | 2 | qbittorrent | ok | 71.72 | 38.93 | 2,878.70 | 29.70 | 97.45 | 160.53 | 1,536.05 | 66 |
| 11 | 2 | transmission | ok | 182.60 | 15.29 | 3,014.47 | 43.35 | 49.79 | 64.65 | 1,536.76 | 223 |
| 12 | 2 | rtorrent | ok | 72.71 | 38.40 | 2,941.80 | 34.50 | 8.64 | 1,225.43 | 1,536.84 | 139 |
| 13 | 3 | rtorrent | ok | 72.77 | 38.37 | 2,922.64 | 31.03 | 7.51 | 1,267.33 | 1,536.56 | 140 |
| 14 | 3 | transmission | timeout | 900.16 | — | 3,005.46 | 62.30 | 41.94 | 57.34 | 1,536.45 | 1557 |
| 15 | 3 | qbittorrent | ok | 85.08 | 32.82 | 2,879.16 | 29.91 | 35.21 | 65.72 | 1,535.99 | 44 |
| 16 | 3 | aria2 | ok | 102.79 | 27.16 | 2,892.47 | 30.12 | 12.31 | 21.43 | 1,536.41 | 199 |
| 17 | 3 | deluge | timeout | 900.03 | — | 3.58 | 25.36 | 81.64 | 142.41 | 88.54 | 1701 |
| 18 | 3 | rqbit | ok | 73.82 | 37.83 | 3,103.25 | 33.45 | 19.92 | 32.61 | 1,536.08 | 43 |
| 19 | 4 | transmission | ok | 113.55 | 24.59 | 2,908.27 | 30.38 | 29.14 | 44.14 | 1,536.64 | 218 |
| 20 | 4 | aria2 | ok | 44.20 | 63.18 | 2,892.27 | 26.73 | 11.02 | 20.05 | 1,536.12 | 86 |
| 21 | 4 | rtorrent | ok | 63.78 | 43.78 | 2,883.56 | 33.75 | 10.24 | 1,347.00 | 1,537.44 | 123 |
| 22 | 4 | rqbit | ok | 76.61 | 36.45 | 3,228.88 | 35.79 | 19.52 | 32.21 | 1,536.04 | 32 |
| 23 | 4 | qbittorrent | ok | 91.25 | 30.60 | 2,871.34 | 30.19 | 37.49 | 67.32 | 1,536.03 | 43 |
| 24 | 4 | deluge | ok | 245.77 | 11.36 | 3,045.96 | 114.86 | 114.68 | 1,504.23 | 1,536.50 | 178 |
| 25 | 5 | qbittorrent | ok | 119.62 | 23.34 | 2,895.69 | 36.44 | 47.09 | 77.56 | 1,536.62 | 73 |
| 26 | 5 | rtorrent | ok | 73.16 | 38.17 | 2,869.06 | 30.67 | 8.19 | 1,245.37 | 1,536.21 | 141 |
| 27 | 5 | deluge | timeout | 900.19 | — | 3.57 | 24.38 | 83.43 | 143.97 | 90.12 | 1698 |
| 28 | 5 | transmission | ok | 347.72 | 8.03 | 3,030.92 | 48.28 | 44.56 | 59.43 | 1,536.54 | 498 |
| 29 | 5 | rqbit | ok | 81.39 | 34.31 | 3,197.98 | 35.64 | 19.87 | 32.55 | 1,536.20 | 36 |
| 30 | 5 | aria2 | ok | 32.85 | 84.99 | 2,842.10 | 22.51 | 7.33 | 16.55 | 1,536.05 | 64 |
| 31 | 6 | deluge | timeout | 900.21 | — | 3.59 | 24.23 | 82.16 | 142.56 | 88.82 | 1699 |
| 32 | 6 | qbittorrent | ok | 76.16 | 36.66 | 2,878.53 | 29.02 | 38.48 | 69.16 | 1,535.98 | 51 |
| 33 | 6 | rqbit | ok | 77.12 | 36.20 | 3,099.69 | 33.55 | 19.68 | 32.37 | 1,537.28 | 26 |
| 34 | 6 | rtorrent | ok | 50.27 | 55.55 | 2,895.48 | 28.00 | 6.48 | 1,329.41 | 1,535.96 | 98 |
| 35 | 6 | aria2 | ok | 289.25 | 9.65 | 2,864.94 | 25.55 | 9.41 | 18.50 | 1,535.99 | 550 |
| 36 | 6 | transmission | ok | 192.27 | 14.52 | 2,963.88 | 42.67 | 45.30 | 61.07 | 1,537.13 | 243 |

Audit: 36 attempts; 30 independent SHA-256 checks; 14,238 resource samples; 920 sanitized Ethernet/route observations. No ISO retained.

This experiment describes cold client state on this host, network, and swarm during the recorded window. It does not estimate universal client capacity. Six trials still have substantial uncertainty; even 6/6 completions gives a Wilson lower bound of about 61%, under a binomial model. Swarm and temporal dependence further limit that model. There are no significance claims.
