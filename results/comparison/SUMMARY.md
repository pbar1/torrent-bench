# Measured results

Rates are MiB/s; values are the median across repetitions. Min–max ranges and all CPU/memory counters are in `summary.csv` and `trials.json`.

| Client | 4 GiB down | 2,048 files | 64 torrents | Capped down | 2-peer upload | Recheck |
|---|---:|---:|---:|---:|---:|---:|
| qbittorrent | 399.1 | 250.3 | 179.5 | 29.9 | 367.4 | 1004.4 |
| deluge | 171.1 | 96.5 | 61.8 | 26.0 | 337.1 | 1121.8 |
| transmission | 91.2 | 50.8 | 47.1 | 23.2 | 242.6 | 1615.2 |
| rtorrent | 257.2 | 257.4 | 66.9 | 30.7 | 96.0 | 1492.3 |
| rqbit | 352.4 | 349.4 | 410.3 | 31.5 | 390.3 | 1647.3 |

Transfer rate between the first samples at or above 10% and 90% of the payload. This reduces startup/completion effects; very short transfers may not have enough samples.

| Client | Large active rate | Large first payload, s | Upload active rate | Upload first payload, s | Capped active rate |
|---|---:|---:|---:|---:|---:|
| qbittorrent | 484.2 | 1.2 | 400.6 | 0.3 | 31.9 |
| deluge | 227.2 | 4.9 | 343.5 | 0.2 | 32.0 |
| transmission | 124.6 | 11.2 | 367.3 | 10.4 | 31.8 |
| rtorrent | — | — | 337.5 | 60.8 | — |
| rqbit | — | — | 406.1 | 0.3 | 31.8 |

Memory in MiB. RSS includes mapped/shared pages; container total includes charged disk cache.

| Client | Empty idle RSS | 64 seeds idle RSS | 1,000 paused idle RSS | Highest sampled RSS | Highest anonymous | Highest container total |
|---|---:|---:|---:|---:|---:|---:|
| qbittorrent | 33.7 | 71.8 | 52.1 | 158.9 | 131.8 | 1550.6 |
| deluge | 138.8 | 160.0 | 180.2 | 3340.8 | 222.2 | 1554.7 |
| transmission | 16.1 | 18.7 | 25.3 | 81.0 | 67.0 | 1537.1 |
| rtorrent | 13.0 | 17.5 | 30.8 | 1429.2 | 18.7 | 1551.1 |
| rqbit | 9.6 | 16.7 | 17.1 | 23.7 | 12.3 | 1536.1 |

| Client | Workload | n | Wall time median (min–max), s | CPU median, core-seconds | Peak RSS, MiB |
|---|---|---:|---:|---:|---:|
| qbittorrent | download-large | 3 | 10.26 (10.18–11.69) | 11.89 | 158.9 |
| qbittorrent | download-files | 3 | 4.09 (2.84–4.30) | 2.74 | 152.4 |
| qbittorrent | download-concurrent | 3 | 5.70 (4.14–10.29) | 2.74 | 119.7 |
| qbittorrent | download-shaped | 3 | 34.27 (34.24–34.36) | 3.78 | 53.7 |
| qbittorrent | upload-2-peers | 3 | 22.30 (19.90–22.90) | 19.15 | 69.2 |
| qbittorrent | recheck-large | 3 | 4.08 (3.41–4.52) | 3.41 | 78.6 |
| qbittorrent | idle-empty | 3 | 15.01 (15.01–15.01) | 0.01 | 34.0 |
| qbittorrent | idle-64-seeds | 3 | 15.00 (15.00–15.01) | 0.03 | 103.7 |
| qbittorrent | add-1000-paused | 3 | 1.34 (1.33–1.35) | 0.62 | 53.0 |
| qbittorrent | idle-1000-paused | 3 | 15.00 (15.00–15.00) | 0.02 | 53.0 |
| deluge | download-large | 3 | 23.94 (22.81–24.78) | 36.09 | 1500.0 |
| deluge | download-files | 3 | 10.62 (10.45–10.99) | 5.54 | 165.1 |
| deluge | download-concurrent | 3 | 16.57 (15.80–26.01) | 5.78 | 462.8 |
| deluge | download-shaped | 3 | 39.35 (39.32–39.35) | 9.10 | 1163.1 |
| deluge | upload-2-peers | 3 | 24.30 (21.85–27.75) | 27.40 | 1360.8 |
| deluge | recheck-large | 3 | 3.65 (3.20–3.99) | 3.07 | 3340.8 |
| deluge | idle-empty | 3 | 15.00 (15.00–15.01) | 0.09 | 140.4 |
| deluge | idle-64-seeds | 3 | 15.00 (15.00–15.01) | 0.08 | 165.1 |
| deluge | add-1000-paused | 3 | 2.38 (2.36–2.54) | 3.10 | 182.7 |
| deluge | idle-1000-paused | 3 | 15.00 (15.00–15.00) | 0.09 | 182.7 |
| transmission | download-large | 3 | 44.92 (44.72–45.25) | 9.42 | 24.3 |
| transmission | download-files | 3 | 20.15 (19.80–20.36) | 2.00 | 23.1 |
| transmission | download-concurrent | 3 | 21.76 (14.04–51.83) | 2.12 | 63.9 |
| transmission | download-shaped | 3 | 44.09 (43.82–44.20) | 3.39 | 23.1 |
| transmission | upload-2-peers | 3 | 33.76 (33.71–34.29) | 11.50 | 81.0 |
| transmission | recheck-large | 3 | 2.54 (2.43–2.90) | 2.21 | 16.8 |
| transmission | idle-empty | 3 | 15.00 (15.00–15.01) | 0.04 | 16.2 |
| transmission | idle-64-seeds | 3 | 15.00 (15.00–15.00) | 0.10 | 20.4 |
| transmission | add-1000-paused | 3 | 0.43 (0.43–0.45) | 0.23 | 25.1 |
| transmission | idle-1000-paused | 3 | 15.00 (15.00–15.00) | 0.09 | 25.6 |
| rtorrent | download-large | 3 | 15.93 (14.78–17.78) | 12.70 | 1429.2 |
| rtorrent | download-files | 3 | 3.98 (3.32–4.18) | 2.75 | 953.7 |
| rtorrent | download-concurrent | 3 | 15.31 (2.59–27.69) | 2.62 | 252.8 |
| rtorrent | download-shaped | 3 | 33.38 (33.36–33.76) | 3.50 | 994.1 |
| rtorrent | upload-2-peers | 3 | 85.34 (84.93–88.17) | 10.75 | 7.6 |
| rtorrent | recheck-large | 3 | 2.74 (2.38–2.91) | 2.73 | 7.9 |
| rtorrent | idle-empty | 3 | 15.00 (15.00–15.01) | 0.00 | 13.2 |
| rtorrent | idle-64-seeds | 3 | 15.00 (15.00–15.01) | 0.01 | 17.6 |
| rtorrent | add-1000-paused | 3 | 0.91 (0.91–1.28) | 0.98 | 30.8 |
| rtorrent | idle-1000-paused | 3 | 15.00 (15.00–15.00) | 0.02 | 30.8 |
| rqbit | download-large | 3 | 11.62 (11.42–12.15) | 16.92 | 13.7 |
| rqbit | download-files | 3 | 2.93 (2.91–3.21) | 3.74 | 16.3 |
| rqbit | download-concurrent | 3 | 2.50 (1.99–3.75) | 3.41 | 23.7 |
| rqbit | download-shaped | 3 | 32.49 (32.44–32.68) | 4.66 | 13.4 |
| rqbit | upload-2-peers | 3 | 20.99 (20.71–24.88) | 19.75 | 12.7 |
| rqbit | recheck-large | 3 | 2.49 (2.48–2.57) | 2.33 | 13.3 |
| rqbit | idle-empty | 3 | 15.00 (15.00–15.00) | 0.00 | 9.6 |
| rqbit | idle-64-seeds | 3 | 15.00 (15.00–15.01) | 0.67 | 17.0 |
| rqbit | add-1000-paused | 3 | 1.40 (1.39–1.41) | 1.12 | 17.1 |
| rqbit | idle-1000-paused | 3 | 15.01 (15.00–15.01) | 0.02 | 17.1 |
