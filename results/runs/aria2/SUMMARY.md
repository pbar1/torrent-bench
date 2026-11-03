# Measured results

Rates are MiB/s; values are the median across repetitions. Min–max ranges and all CPU/memory counters are in `summary.csv` and `trials.json`.

| Client | 4 GiB down | 2,048 files | 64 torrents | Capped down | 2-peer upload | Recheck |
|---|---:|---:|---:|---:|---:|---:|
| aria2 | 183.6 | 133.9 | 207.4 | 30.0 | 218.2 | 332.0 |

Transfer rate between the first samples at or above 10% and 90% of the payload. This reduces startup/completion effects; very short transfers may not have enough samples.

| Client | Large active rate | Large first payload, s | Upload active rate | Upload first payload, s | Capped active rate |
|---|---:|---:|---:|---:|---:|
| aria2 | 204.7 | 2.3 | 261.4 | 1.2 | 32.1 |

Memory in MiB. RSS includes mapped/shared pages; container total includes charged disk cache.

| Client | Empty idle RSS | 64 seeds idle RSS | 1,000 paused idle RSS | Highest sampled RSS | Highest anonymous | Highest container total |
|---|---:|---:|---:|---:|---:|---:|
| aria2 | 12.3 | 16.0 | 26.6 | 26.7 | 18.2 | 1537.9 |

| Client | Workload | n | Wall time median (min–max), s | CPU median, core-seconds | Peak RSS, MiB |
|---|---|---:|---:|---:|---:|
| aria2 | download-large | 3 | 22.31 (21.17–28.37) | 18.05 | 16.8 |
| aria2 | download-files | 3 | 7.65 (7.13–8.59) | 5.17 | 20.0 |
| aria2 | download-concurrent | 3 | 4.94 (4.77–14.49) | 3.99 | 20.4 |
| aria2 | download-shaped | 3 | 34.14 (34.04–34.44) | 4.74 | 16.8 |
| aria2 | upload-2-peers | 3 | 37.54 (28.32–40.77) | 14.33 | 26.7 |
| aria2 | recheck-large | 3 | 12.34 (11.79–12.34) | 11.41 | 13.7 |
| aria2 | idle-empty | 3 | 15.00 (15.00–15.00) | 0.00 | 12.6 |
| aria2 | idle-64-seeds | 3 | 15.00 (15.00–15.00) | 0.64 | 17.1 |
| aria2 | add-1000-paused | 3 | 0.44 (0.44–2.35) | 0.12 | 26.6 |
| aria2 | idle-1000-paused | 3 | 15.01 (15.00–15.01) | 0.00 | 26.6 |
