# Repeated public Ubuntu fresh-download experiment

Six registered attempts per client, 6 total; a fixed 900-second deadline, without an early stall cutoff. Median, interquartile range (IQR), and full range describe completed, SHA-256 verified downloads. Every failure remains in the completion count and receives 900 seconds in the penalized mean. Inclusive quartiles use linear interpolation at rank (n−1)×p. Speed and duration medians are computed separately from per-attempt values.

| Client | Completed | Wilson 95% completion interval | Median MiB/s | IQR MiB/s | Range MiB/s | Median seconds | Mean penalized seconds |
|---|---:|---:|---:|---:|---:|---:|---:|
| deluge | 6/6 | 61.0%–100.0% | 17.31 | 15.60–19.40 | 11.28–20.78 | 161.99 | 171.49 |

**All-attempt resource costs, including failed/partial work.** Memory cells show the median of per-attempt sampled peaks / the largest sampled peak. Charged memory includes filesystem cache; RSS includes resident mappings; anonymous memory isolates resident allocations. These are different counters.

| Client | CPU core-s median (range) | Peak anonymous MiB, median / max | Peak RSS MiB, median / max | Peak charged MiB, median / max | Peak working MiB, median / max |
|---|---:|---:|---:|---:|---:|
| deluge | 70.39 (61.21–98.23) | 155.56 / 179.88 | 1,493.55 / 1,520.41 | 1,537.09 / 1,540.48 | 1,396.60 / 1,435.78 |

**Completed-download resource costs.** The following subset excludes failed attempts, whose resources may cover discovery or only a small part of the ISO. Use this subset for loaded-download comparisons. Cells again show median / maximum sampled peak; CPU is a median.

| Client | Verified downloads | CPU core-s | Peak anonymous MiB | Peak RSS MiB | Peak charged MiB | Peak working MiB |
|---|---:|---:|---:|---:|---:|---:|
| deluge | 6 | 70.39 | 155.56 / 179.88 | 1,493.55 / 1,520.41 | 1,537.09 / 1,540.48 | 1,396.60 / 1,435.78 |

**Discovery and observation quality.** Startup/active rates are omitted for rqbit and rTorrent because their counters can include initialization or hash-scan work. A dash also denotes unavailable address-family counters (not captured for rqbit). Peer maxima are sampled address counts from native APIs, with different client semantics, not unique-peer totals or a normalized capacity measure. Sampling intervals are median / maximum seconds; resource peaks can miss brief spikes, especially during the longer gaps.

| Client | First payload s (valid n) | Active 10–90% MiB/s (valid n) | Max observed IPv4 peers | Max observed IPv6 peers | Resource interval s | Status interval s |
|---|---:|---:|---:|---:|---:|---:|
| deluge | 5.04 (6) | 19.64 (6) | — | — | 0.528 / 8.075 | 0.204 / 0.255 |

**Every registered attempt, in execution order.** Network receive bytes include BitTorrent and control/protocol traffic. The complete-file rate is absent on failure. CPU and sampled memory peaks describe that attempt; the sample count makes uneven resource observation visible.

| Slot | Round | Client | Result | Seconds | MiB/s | Received MiB | CPU core-s | Peak anonymous MiB | Peak RSS MiB | Peak charged MiB | Samples |
|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1 | deluge | ok | 181.33 | 15.40 | 3,033.69 | 85.76 | 136.95 | 1,445.54 | 1,537.11 | 318 |
| 2 | 2 | deluge | ok | 141.62 | 19.72 | 2,947.97 | 63.81 | 160.29 | 1,452.12 | 1,536.94 | 135 |
| 3 | 3 | deluge | ok | 134.36 | 20.78 | 2,935.09 | 65.05 | 158.96 | 1,520.41 | 1,536.01 | 87 |
| 4 | 4 | deluge | ok | 247.65 | 11.28 | 3,030.57 | 98.23 | 145.07 | 1,507.91 | 1,537.07 | 297 |
| 5 | 5 | deluge | ok | 151.46 | 18.44 | 2,960.06 | 61.21 | 152.15 | 1,507.68 | 1,540.48 | 152 |
| 6 | 6 | deluge | ok | 172.52 | 16.18 | 3,001.49 | 75.74 | 179.88 | 1,479.43 | 1,537.15 | 291 |

Audit: 6 attempts; 6 independent SHA-256 checks; 1,280 resource samples; 112 sanitized Ethernet/route observations. No ISO retained.

This experiment describes cold client state on this host, network, and swarm during the recorded window. It does not estimate universal client capacity. Six trials still have substantial uncertainty; even 6/6 completions gives a Wilson lower bound of about 61%, under a binomial model. Swarm and temporal dependence further limit that model. There are no significance claims.
