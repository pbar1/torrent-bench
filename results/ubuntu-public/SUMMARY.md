# Public Ubuntu fresh-download results

1 fresh attempt(s) per client, one ISO at a time. Rates include discovery and completion. Only completed, independently SHA-256 verified downloads receive a full-file rate. Memory peaks cover all attempts; charged memory includes disk cache. The ISO is deleted after every attempt.

| Client | Completed | Median MiB/s | Min–max MiB/s | Median seconds | CPU core-seconds | Peak RSS MiB | Peak anonymous MiB | Peak charged MiB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qbittorrent | 1/1 | 28.32 | 28.32–28.32 | 98.58 | 35.35 | 67.09 | 36.99 | 1536.00 |
| deluge | 1/1 | 18.96 | 18.96–18.96 | 147.26 | 64.58 | 1505.84 | 151.14 | 1536.84 |
| transmission | 1/1 | 7.39 | 7.39–7.39 | 378.03 | 50.54 | 54.65 | 39.32 | 1536.50 |
| rtorrent | 0/1 | — | —–— | — | 0.67 | 16.49 | 4.04 | 6.92 |
| rqbit | 1/1 | 39.37 | 39.37–39.37 | 70.93 | 37.51 | 32.72 | 20.04 | 1551.34 |
| aria2 | 0/1 | — | —–— | — | 3.03 | 14.70 | 5.62 | 41.68 |

The public swarm, ISP, peer mix, and network congestion are uncontrolled. These observations measure this host and time window, rather than each client’s maximum capacity. Docker uses IPv4 NAT without forwarded incoming ports. See `trials.json` for each repetition, startup/active-window diagnostics, upload traffic, verification, and cleanup; `validation.json` audits completeness and raw resource sample counts.
