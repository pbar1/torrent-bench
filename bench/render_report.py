"""Regenerate the standalone browser report from REPORT.md and recorded data."""
import csv
import hashlib
import html
import json
import re
from pathlib import Path
from analyze_ubuntu import distribution

root = Path(__file__).resolve().parents[1]
report = (root / 'REPORT.md').read_text()
rows = list(csv.DictReader((root / 'results/comparison/summary.csv').open()))
names = {'qbittorrent': 'qBittorrent', 'deluge': 'Deluge', 'transmission': 'Transmission', 'rtorrent': 'rTorrent', 'rqbit': 'rqbit', 'aria2': 'aria2'}
workloads = {'idle-empty': 'Empty idle', 'download-large': '4 GiB download', 'recheck-large': '4 GiB recheck', 'upload-2-peers': 'Two-peer upload', 'download-files': '2,048 files', 'download-concurrent': '64 torrents', 'idle-64-seeds': '64 seeds idle', 'download-shaped': 'Capped download', 'add-1000-paused': 'Register 1,000 paused', 'idle-1000-paused': '1,000 paused idle'}
public_path = root / 'results/ubuntu-six-runs'
public_trials = json.loads((public_path / 'trials.json').read_text())
public_validation = json.loads((public_path / 'validation.json').read_text())
assert public_validation['ok'] and len(public_trials) == 36
assert hashlib.sha256((public_path / 'trials.json').read_bytes()).hexdigest() == public_validation['input_sha256']['trials.json']
followup_path = root / 'results/ubuntu-deluge-ipv6'
followup_trials = json.loads((followup_path / 'trials.json').read_text())
followup_validation = json.loads((followup_path / 'validation.json').read_text())
assert followup_validation['ok'] and len(followup_trials) == 6
assert hashlib.sha256((followup_path / 'trials.json').read_bytes()).hexdigest() == followup_validation['input_sha256']['trials.json']


def public_chart():
    metrics = [('mib_s', 'Complete-file throughput, MiB/s', 'Higher is faster; completed downloads only.'),
               ('penalized_s', 'Deadline-penalized time, seconds', 'Lower is faster; a failed attempt receives 900 seconds.'),
               ('peak_anon_mib', 'Peak anonymous memory, MiB', 'Resident application allocations; all attempts.'),
               ('peak_rss_mib', 'Peak RSS, MiB', 'Resident process pages, including mappings; all attempts.'),
               ('peak_memory_mib', 'Peak charged memory, MiB', 'Container memory including filesystem cache; all attempts.'),
               ('cpu_s', 'CPU cost, core-seconds', 'CPU time accumulated during the measured download; all attempts.')]
    panels = []
    for key, title, description in metrics:
        def value(t):
            if key == 'mib_s':
                return t['mib_s']
            if key == 'penalized_s':
                return t['elapsed_s'] if t['status'] == 'ok' else 900
            return t['metrics']['client'][key]
        ceiling = max(value(t) for t in public_trials if value(t) is not None) * 1.06
        bars = []
        for client, name in names.items():
            items = [t for t in public_trials if t['client'] == client and value(t) is not None]
            stats = distribution(value(t) for t in items)
            if not items:
                bars.append(f'<div class="public-row"><span class="bar-name">{name}</span><span>No completed download</span></div>')
                continue
            scale = lambda v: v / ceiling * 100
            track = [f'<span class="public-range" style="left:{scale(stats["min"]):.4f}%;width:{scale(stats["max"] - stats["min"]):.4f}%"></span>',
                     f'<span class="public-iqr" style="left:{scale(stats["q1"]):.4f}%;width:{scale(stats["q3"] - stats["q1"]):.4f}%"></span>',
                     f'<span class="public-median" style="left:{scale(stats["median"]):.4f}%"></span>']
            for t in items:
                label = html.escape(f'Round {t["repeat"] + 1}: {value(t):.2f}; {t["status"]}')
                track.append(f'<span class="public-point{" incomplete" if t["status"] != "ok" else ""}" '
                             f'style="left:{scale(value(t)):.4f}%;top:{4 + t["repeat"] * 4}px" '
                             f'role="img" aria-label="{label}" title="{label}"></span>')
            bars.append(f'<div class="public-row"><span class="bar-name">{name}</span>'
                        f'<div class="public-track">{"".join(track)}</div>'
                        f'<span class="bar-number"><strong>{stats["median"]:.1f}</strong>'
                        f'<small>{len(items)} observations</small></span></div>')
        panels.append(f'<div class="public-panel" data-metric="{key}"' + (' hidden' if key != 'mib_s' else '') + '>'
                      f'<p class="public-description"><strong>{title}.</strong> {description}</p>{"".join(bars)}'
                      f'<div class="public-axis"><span></span><span>0 <span>{ceiling:.1f}</span></span><span>Median</span></div></div>')
    options = ''.join(f'<option value="{key}">{title}</option>' for key, title, _ in metrics)
    return ('<figure class="chart public-chart" aria-labelledby="public-chart-title">'
            '<div class="chart-top"><div><h3 id="public-chart-title">Every observation in the main experiment</h3>'
            '<p>Six registered attempts per client. Hover over a point for its round and value.</p></div>'
            f'<div class="chart-control" id="public-chart-control" hidden><label for="public-metric">Compare metric</label>'
            f'<select id="public-metric">{options}</select></div></div>' + ''.join(panels) +
            '<figcaption>Each dot is one attempt; the shaded band is the interquartile range, '
            'the vertical line is the median, and the thin line is the full range. '
            'These ranges describe observations, not confidence intervals. Hollow dots indicate failed attempts. '
            'Failures receive no complete-file speed.</figcaption></figure>')

def inline(text):
    text = html.escape(text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)

def table(lines, caption):
    cells = lambda line: [c.strip() for c in line.strip().strip('|').split('|')]
    head, alignment = cells(lines[0]), cells(lines[1])
    out = ['<div class="table-scroll" role="region" tabindex="0" aria-label="' + html.escape(caption) + '"><table><caption class="sr-only">' + html.escape(caption) + '</caption><thead><tr>']
    out += ['<th scope="col"' + (' class="num"' if a.endswith(':') else '') + '>' + inline(c) + '</th>' for c, a in zip(head, alignment)]
    out += ['</tr></thead><tbody>']
    for line in lines[2:]:
        out += ['<tr>']
        for i, (c, a) in enumerate(zip(cells(line), alignment)):
            tag = 'th scope="row"' if i == 0 else 'td'
            out += ['<' + tag + (' class="num"' if a.endswith(':') else '') + '>' + inline(c) + ('</th>' if i == 0 else '</td>')]
        out += ['</tr>']
    return '\n'.join(out + ['</tbody></table></div>'])

# REPORT.md uses only paragraphs, headings, inline formatting, and tables.
sections = []
current = {'id': 'overview', 'title': 'Findings at a glance', 'blocks': []}
paragraph = []
lines = report.splitlines()
i = 1
while i < len(lines):
    line = lines[i]
    if not line.strip() or line.startswith('## ') or line.startswith('|'):
        if paragraph:
            current['blocks'].append('<p>' + inline(' '.join(paragraph)) + '</p>')
            paragraph = []
    if line.startswith('## '):
        sections.append(current)
        title = line[3:]
        current = {'id': re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-'), 'title': title, 'blocks': []}
    elif line.startswith('|'):
        block = []
        while i < len(lines) and lines[i].startswith('|'):
            block.append(lines[i])
            i += 1
        current['blocks'].append(table(block, current['title']))
        continue
    elif line.strip():
        paragraph.append(line.strip())
    i += 1
if paragraph:
    current['blocks'].append('<p>' + inline(' '.join(paragraph)) + '</p>')
sections.append(current)

chart_rows = [r for r in rows if r['workload'] == 'download-large']
max_rate = max(float(r['max_mib_s']) for r in chart_rows)
best = max(float(r['median_mib_s']) for r in chart_rows)

def bar(r):
    median, low, high = (float(r[k]) for k in ('median_mib_s', 'min_mib_s', 'max_mib_s'))
    return f'''<div class="bar-row"><span class="bar-name">{names[r['client']]}</span><div class="bar-track" aria-hidden="true"><span class="bar-fill{' best' if median == best else ''}" style="width:{median / max_rate * 100:.4f}%"></span><span class="bar-range" style="left:{low / max_rate * 100:.4f}%;width:{(high-low) / max_rate * 100:.4f}%"></span></div><span class="bar-number"><strong>{median:.1f}</strong><small>{low:.1f}–{high:.1f}</small></span></div>'''

chart = '''<figure class="chart" aria-labelledby="chart-title">
<div class="chart-top"><div><h3 id="chart-title">4 GiB download</h3><p id="chart-description">Median throughput and observed min–max, MiB/s. Higher is faster.</p></div>
<div class="chart-control" id="chart-control" hidden><label for="workload">Compare workload</label><select id="workload"><option value="download-large">4 GiB download</option><option value="download-files">2,048 files</option><option value="download-concurrent">64 torrents</option><option value="download-shaped">32 MiB/s capped</option><option value="upload-2-peers">Two-peer upload</option></select></div></div>
<div id="chart-bars" aria-describedby="chart-description">''' + '\n'.join(bar(r) for r in chart_rows) + '''</div>
<figcaption><span class="legend-mark"></span>Highest median <span class="range-mark"></span>Observed min–max across three repetitions. Ranges are not confidence intervals.</figcaption>
</figure>'''

body = []
for number, section in enumerate(sections):
    content = list(section['blocks'])
    if section['id'] == 'transfer-results':
        content.insert(1, chart)
    if section['id'] == 'ubuntu-public-download':
        first_table = next(i for i, block in enumerate(content) if block.startswith('<div class="table-scroll"'))
        content.insert(first_table, public_chart())
    if section['id'] == 'scope-and-reproduction':
        content += ['''<pre aria-label="Reproduce the benchmark"><code>./run.sh --output my-run --repeats 3
python3 bench/summarize.py results/my-run
python3 bench/validate_results.py results/my-run</code></pre>''']
    body.append(f'<section id="{section["id"]}" aria-labelledby="heading-{section["id"]}"><div class="section-heading"><span class="section-number">{number:02d}</span><h2 id="heading-{section["id"]}">{section["title"]}</h2></div>' + '\n'.join(content) + '</section>')

measurements = []
for client in names:
    for workload in workloads:
        r = next(r for r in rows if r['client'] == client and r['workload'] == workload)
        rate = f"{float(r['median_mib_s']):.1f}" if r['median_mib_s'] else '—'
        measurements.append(f'''<tr data-client="{client}"><th scope="row">{names[client]}</th><td>{workloads[workload]}</td><td class="num">{r['n']}</td><td class="num">{float(r['median_s']):.2f}<small class="cell-range">{float(r['min_s']):.2f}–{float(r['max_s']):.2f}</small></td><td class="num">{rate}</td><td class="num">{float(r['median_cpu_s']):.2f}</td><td class="num">{float(r['median_rss_mib']):,.1f}</td><td class="num">{float(r['peak_rss_mib']):,.1f}</td><td class="num">{float(r['peak_anon_mib']):,.1f}</td><td class="num">{float(r['peak_container_mib']):,.1f}</td><td class="num">{float(r['peak_working_mib']):,.1f}</td></tr>''')

active_lines = (root / 'results/comparison/SUMMARY.md').read_text().splitlines()
start = next(i for i, line in enumerate(active_lines) if line.startswith('| Client | Large active rate'))
active_table = table(active_lines[start:start+len(names)+2], 'Valid active-window rates and first observed payload times')

style = '''
:root{color-scheme:light;--ink:#192b38;--muted:#536773;--line:#dce3e8;--paper:#fff;--ground:#f5f7f8;--accent:#17618a;--green:#08795e;--soft:#eaf4ef;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:16px}
*{box-sizing:border-box}.skip-link{position:absolute;top:10px;left:10px;z-index:10;background:white;padding:10px;transform:translateY(-200%)}.skip-link:focus{transform:translateY(0)}html{scroll-behavior:smooth;scroll-padding-top:95px}body{margin:0;background:var(--ground);color:var(--ink);line-height:1.7}a{color:var(--accent);text-decoration-thickness:1px;text-underline-offset:3px}a:hover{color:var(--green)}:focus-visible{outline:3px solid #c97920;outline-offset:4px}header{background:var(--paper);border-bottom:1px solid var(--line)}.topline,.navigation,.page,footer{max-width:1180px;margin:auto;padding-left:40px;padding-right:40px}.topline{display:flex;justify-content:space-between;align-items:center;gap:16px;padding-top:20px;padding-bottom:20px;font-size:.78rem;letter-spacing:.09em;text-transform:uppercase}.brand{display:flex;gap:12px;align-items:center;font-weight:750}.brand-icon{display:grid;place-items:center;width:29px;height:29px;border-radius:6px;background:var(--ink);color:white;font-size:20px;line-height:1}.top-meta{color:var(--muted);font-size:.71rem}.nav-shell{position:sticky;top:0;z-index:5;background:rgba(255,255,255,.97);border-bottom:1px solid var(--line)}.navigation{display:flex;gap:28px;overflow:auto;padding-top:13px;padding-bottom:13px}.navigation a{white-space:nowrap;font-size:.82rem;color:var(--muted);text-decoration:none;font-weight:600}.navigation a:hover{color:var(--accent)}.hero{padding:60px 0 10px}.eyebrow{margin:0 0 20px;color:var(--accent);font-size:.72rem;letter-spacing:.14em;text-transform:uppercase;font-weight:750}h1{font-size:clamp(2.6rem,5.1vw,4.25rem);line-height:1.08;letter-spacing:-.045em;margin:0 0 22px;max-width:850px;font-weight:750}.hero-subtitle{font-size:1.08rem;color:var(--muted);max-width:660px;line-height:1.65;margin:0}.stats{display:grid;grid-template-columns:repeat(4,1fr);margin:34px 0 0;padding:24px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}.stat{padding-left:28px;border-left:1px solid var(--line)}.stat:first-child{padding-left:0;border-left:0}.stat strong{font-size:2.1rem;letter-spacing:-.05em;display:block;line-height:1.2;font-weight:700}.stat strong span{font-size:1rem;letter-spacing:0}.stat small{color:var(--muted);font-size:.8rem}.lab-line{display:flex;align-items:center;flex-wrap:wrap;gap:8px 18px;margin:17px 0 0;color:var(--muted);font-size:.77rem}.verified{color:var(--green);font-weight:650}.verified:before{content:"";display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--green);margin-right:7px}main section{padding:38px 0 40px;border-bottom:1px solid var(--line)}.section-heading{display:flex;align-items:baseline;gap:17px;margin-bottom:18px}.section-number{color:#718491;font-size:.75rem;font-weight:650;letter-spacing:.05em}h2{font-size:1.65rem;font-weight:700;letter-spacing:-.025em;margin:0;line-height:1.3}h3{font-size:1.05rem;line-height:1.4;margin:0;letter-spacing:-.01em}section>p{max-width:86ch;margin:16px 0;font-size:.98rem}strong{font-weight:700}code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:.87em;background:#e9eef1;padding:.13em .3em;border-radius:3px;overflow-wrap:anywhere}pre{background:var(--ink);color:#e5f4f8;border-radius:9px;padding:24px;overflow:auto;line-height:1.85;font-size:.85rem;margin:24px 0 0}pre code{background:none;padding:0;color:inherit;font-size:inherit;white-space:pre}table{width:100%;border-collapse:collapse;background:white;font-size:.84rem;line-height:1.55;font-variant-numeric:tabular-nums}th,td{padding:13px 16px;text-align:left;vertical-align:top;border-bottom:1px solid #e7ecef}thead th{font-size:.73rem;color:#455e6c;font-weight:650;background:#eef3f5;vertical-align:bottom}tbody th{font-weight:650;white-space:nowrap}tbody tr:last-child>*{border-bottom:0}tbody tr:hover{background:#f6f9fa}.num{text-align:right;white-space:nowrap}.table-scroll{width:100%;overflow-x:auto;border:1px solid var(--line);border-radius:9px;margin:24px 0;background:white}.table-scroll:focus{outline-offset:3px}.table-scroll table{min-width:660px}.chart{margin:27px 0;background:white;border:1px solid var(--line);border-radius:10px;padding:27px 28px 20px}.chart-top{display:flex;align-items:flex-start;justify-content:space-between;gap:22px;margin-bottom:25px}.chart-top p{font-size:.79rem;color:var(--muted);margin:5px 0 0;max-width:49ch}.chart-control label{font-size:.7rem;color:var(--muted);display:block;margin-bottom:5px}select{font:inherit;font-size:.81rem;border:1px solid #b9c9d2;border-radius:5px;background:white;color:var(--ink);padding:8px 30px 8px 10px;max-width:100%}.bar-row{display:grid;grid-template-columns:130px 1fr 95px;gap:18px;align-items:center;padding:10px 0}.bar-name{font-size:.85rem;font-weight:600}.bar-track{position:relative;height:21px;background:#f0f4f6;border-radius:3px}.bar-fill{display:block;position:absolute;top:0;left:0;height:100%;background:#6595b2;border-radius:3px}.bar-fill.best{background:var(--green)}.bar-range{display:block;position:absolute;top:50%;height:2px;margin-top:-1px;background:var(--ink);min-width:1px}.bar-range:before,.bar-range:after{content:"";height:10px;width:1px;background:var(--ink);position:absolute;top:-4px}.bar-range:before{left:0}.bar-range:after{right:0}.bar-number{font-variant-numeric:tabular-nums;text-align:right;line-height:1.25}.bar-number strong{font-size:1rem}.bar-number small{display:block;font-size:.66rem;color:var(--muted);margin-top:3px}.chart figcaption{font-size:.72rem;color:var(--muted);border-top:1px solid var(--line);padding-top:15px;margin-top:18px;line-height:1.7}.legend-mark{display:inline-block;width:8px;height:8px;background:var(--green);margin-right:6px}.range-mark{display:inline-block;width:16px;border-top:2px solid var(--ink);vertical-align:middle;margin:0 6px 0 17px}.measurement-control{display:flex;align-items:center;justify-content:space-between;gap:15px;margin:22px 0 0;font-size:.8rem}.measurement-control label{margin-right:10px;color:var(--muted)}.row-count{color:var(--muted);font-size:.76rem}.measurements table{min-width:1190px}.measurements th,.measurements td{padding:11px 12px}.measurements td:nth-child(2){white-space:nowrap}.cell-range{display:block;color:var(--muted);font-size:.68rem;margin-top:3px}.measurement-key{font-size:.79rem!important;color:var(--muted);max-width:none!important}.resource-links{display:flex;flex-wrap:wrap;gap:10px 25px;font-size:.84rem;margin:22px 0}.resources-note{color:var(--muted);font-size:.84rem!important}.source-list{display:flex;flex-wrap:wrap;gap:8px 22px;font-size:.82rem;margin:18px 0 0}.source-list a{white-space:nowrap}footer{padding-top:27px;padding-bottom:35px;color:var(--muted);font-size:.75rem;display:flex;justify-content:space-between;gap:15px}footer a{color:inherit}.sr-only{position:absolute;width:1px;height:1px;margin:-1px;padding:0;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}[hidden]{display:none!important}
@media(max-width:700px){.topline,.navigation,.page,footer{padding-left:22px;padding-right:22px}.topline{padding-top:15px;padding-bottom:15px}.top-meta{display:none}.navigation{gap:22px}.hero{padding-top:35px}h1{font-size:2.65rem}.hero-subtitle{font-size:.97rem}.stats{grid-template-columns:repeat(2,1fr);gap:22px 0;margin-top:26px}.stat{padding-left:20px}.stat:nth-child(3){padding-left:0;border:0}.stat strong{font-size:1.85rem}.lab-line{font-size:.72rem}main section{padding:29px 0 31px}.section-heading{gap:12px}h2{font-size:1.35rem}section>p{font-size:.92rem;line-height:1.75}.chart{padding:20px 15px 16px}.chart-top{flex-direction:column;gap:14px}.chart-control{width:100%}.chart-control select{width:100%}.bar-row{grid-template-columns:90px 1fr 68px;gap:9px;padding:11px 0}.bar-name{font-size:.73rem}.bar-track{height:18px}.bar-number strong{font-size:.87rem}.bar-number small{font-size:.59rem}.chart figcaption{font-size:.66rem}.range-mark{margin-left:9px}.measurement-control{flex-wrap:wrap}th,td{padding:11px 13px}pre{padding:18px;font-size:.72rem}footer{flex-direction:column}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
@media print{@page{size:A4 landscape;margin:15mm}body{background:white;color:black;font-size:10pt}.topline,.navigation,.page,footer{max-width:none;padding-left:0;padding-right:0}.nav-shell,.chart-control,.measurement-control,.top-meta{display:none!important}.hero{padding-top:0}h1{font-size:30pt}h2{font-size:17pt}.hero-subtitle{font-size:11pt}section>p{max-width:none;font-size:10pt}main section{padding:22px 0}.stats{margin-top:20px}.table-scroll{overflow:visible;border-radius:0}table,.table-scroll table,.measurements table{min-width:0;font-size:8pt}.measurements table{font-size:6.7pt}th,td,.measurements th,.measurements td{padding:6px}.table-scroll,.chart{break-inside:avoid}.measurements{break-inside:auto}tr{break-inside:avoid}thead{display:table-header-group}.chart{padding:18px}.chart-top{margin-bottom:12px}.bar-row{padding:6px 0}.cell-range{font-size:6.5pt}pre{background:#eee;color:black}a{color:inherit}h2,h3{break-after:avoid}tr[hidden]{display:table-row!important}footer{font-size:8pt}.lab-line{font-size:8pt}}
'''

style += '''
.public-row{display:grid;grid-template-columns:130px minmax(0,1fr) 95px;gap:18px;align-items:center;padding:10px 0}.public-track{position:relative;height:34px;background:#f0f4f6;border-radius:3px}.public-point{position:absolute;width:7px;height:7px;margin-left:-3px;border-radius:50%;background:#17618a;border:1px solid white;z-index:2}.public-point.incomplete{background:white;border-color:#a34b2e}.public-range{position:absolute;top:17px;height:1px;background:#81939d}.public-iqr{position:absolute;top:10px;height:15px;background:#c5dfd5}.public-median{position:absolute;top:5px;height:25px;width:2px;margin-left:-1px;background:#08795e;z-index:1}.public-description{font-size:.8rem;color:var(--muted);margin:0 0 16px}.public-axis{display:grid;grid-template-columns:130px minmax(0,1fr) 95px;gap:18px;font-size:.68rem;color:var(--muted)}.public-axis>span:nth-child(2)>span{float:right}.public-axis>span:last-child{text-align:right}
@media(max-width:700px){.public-row,.public-axis{grid-template-columns:90px minmax(0,1fr) 68px;gap:9px}.public-chart .bar-name{font-size:.73rem}.public-chart .chart-control select{font-size:.73rem}}
'''

page = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Measured performance of qBittorrent, Deluge, Transmission, rTorrent, rqbit, and aria2: 180 synthetic phases, 36 main public Ubuntu attempts and six separate Deluge interface attempts, with repeated throughput, CPU, memory, and reproducible Docker Compose methodology.">
<meta name="color-scheme" content="light">
<title>Torrent client comparison — measured performance &amp; memory</title>
<style>''' + style + '''</style>
</head>
<body>
<a class="skip-link" href="#main">Skip to findings</a>
<header><div class="topline"><span class="brand"><span class="brand-icon" aria-hidden="true"><svg width="19" height="19" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 6h13m-4-4 4 4-4 4M17 14H4m4-4-4 4 4 4"/></svg></span>Torrent client benchmarks</span><span class="top-meta">Synthetic lab · Ubuntu public swarm</span></div></header>
<div class="nav-shell"><nav class="navigation" aria-label="Report sections"><a href="#overview">Overview</a><a href="#ubuntu-public-download">Ubuntu download</a><a href="#transfer-results">Synthetic throughput</a><a href="#memory-and-cpu">Memory &amp; CPU</a><a href="#versions-and-conditions">Test setup</a><a href="#validation-and-collection-history">Validation</a><a href="#all-measurements">All measurements</a></nav></div>
<div class="page">
<div class="hero"><p class="eyebrow">BitTorrent benchmarks / 02–03 November 2026</p><h1>Torrent client<br>performance comparison.</h1><p class="hero-subtitle">qBittorrent, Deluge, Transmission, rTorrent, rqbit, and aria2, measured in a controlled Docker lab and on the public Ubuntu swarm over gigabit Ethernet. Throughput, CPU, and memory.</p>
<div class="stats" aria-label="Synthetic benchmark totals"><div class="stat"><strong>180</strong><small>synthetic test phases</small></div><div class="stat"><strong>270 <span>GiB</span></strong><small>synthetic payload transferred</small></div><div class="stat"><strong>3</strong><small>synthetic repetitions / client</small></div><div class="stat"><strong>38,052</strong><small>synthetic SHA-256 file checks</small></div></div>
<p class="lab-line"><a class="verified" href="results/comparison/validation.json">Payload verification passed</a><span>Native ARM64</span><span>2 CPU cores / 1,536 MiB per client</span><span>Main public test: 36 attempts, six per client</span><span>Deluge interface follow-up: six attempts</span><span>1 GbE confirmed</span></p></div>
<main id="main">''' + '\n'.join(body) + '''
<section id="all-measurements" aria-labelledby="heading-all-measurements"><div class="section-heading"><span class="section-number">MEASUREMENT_NUMBER</span><h2 id="heading-all-measurements">All synthetic measurements</h2></div>
<p>Every client and workload, with all three repetitions included. Rates and times are medians; the smaller time range is the observed minimum–maximum. Memory is in MiB. Recheck rates are cached hash-check throughput, not network throughput.</p>
<div class="measurement-control" id="measurement-control" hidden><div><label for="client-filter">Show client</label><select id="client-filter"><option value="all">All clients</option>''' + ''.join(f'<option value="{c}">{n}</option>' for c,n in names.items()) + '''</select></div><span class="row-count" id="row-count" role="status">60 of 60 groups</span></div>
<div class="table-scroll measurements" role="region" tabindex="0" aria-label="All 60 measurement groups; scroll horizontally for memory counters"><table id="measurements"><caption class="sr-only">All 60 client and workload groups, each with three repetitions</caption><thead><tr><th scope="col">Client</th><th scope="col">Workload</th><th scope="col" class="num">n</th><th scope="col" class="num">Time, s<br>median / min–max</th><th scope="col" class="num">Rate<br>MiB/s</th><th scope="col" class="num">CPU<br>core-s</th><th scope="col" class="num">Median<br>RSS</th><th scope="col" class="num">Peak<br>RSS</th><th scope="col" class="num">Peak<br>anonymous</th><th scope="col" class="num">Peak<br>container</th><th scope="col" class="num">Peak<br>working set</th></tr></thead><tbody>''' + '\n'.join(measurements) + '''</tbody></table></div>
<p class="measurement-key">RSS sums process resident pages, including file mappings and shared pages. Anonymous memory measures resident application allocations. Container memory includes charged filesystem cache. Working set is usage minus inactive file pages. Peaks are sampled; these counters are not interchangeable. Scroll the table horizontally on smaller screens.</p>
<h3>Valid active-window diagnostics</h3><p>Active rates use the first progress samples at or above 10% and 90% of payload. Rates are MiB/s; first-payload times are seconds. A dash indicates a suppressed diagnostic because the API progress counter reset during initialization or checking. In particular, rTorrent's capped-download diagnostic was suppressed; its overall capped rate remains valid.</p>''' + active_table + '''</section>
<section id="evidence" aria-labelledby="heading-evidence"><div class="section-heading"><span class="section-number">EVIDENCE_NUMBER</span><h2 id="heading-evidence">Evidence &amp; source files</h2></div><p>This page contains the complete narrative report, 60 synthetic workload groups, all 36 main public Ubuntu attempts, and the six-attempt Deluge interface follow-up. Its charts use embedded measurements and work directly from disk, without a server or internet connection. The linked files retain the underlying precision and resource time series.</p>
<div class="resource-links"><a href="REPORT.md">Narrative source</a><a href="results/comparison/summary.csv">Summary CSV</a><a href="results/comparison/trials.json">All trial records</a><a href="results/comparison/samples.jsonl.gz">Resource time series</a><a href="results/comparison/environment.json">Recorded environment</a><a href="results/comparison/validation.json">Validation audit</a><a href="results/comparison/selection.json">Run selection</a><a href="results/runs/baseline/post-failure-diagnostic.json">Post-failure diagnostic</a><a href="compose.yaml">Docker Compose</a><a href="images.env">Pinned images</a><a href="aria2/Dockerfile">aria2 image build</a><a href="aria2/measured-packages.txt">aria2 package inventory</a><a href="README.md">Setup &amp; methodology</a><a href="results/ubuntu-six-runs/protocol.json">Registered public protocol</a><a href="results/ubuntu-six-runs/analysis.json">Public statistical analysis</a><a href="results/ubuntu-six-runs/attempts.csv">Every public observation CSV</a><a href="results/ubuntu-six-runs/summary.csv">Ubuntu summary CSV</a><a href="results/ubuntu-six-runs/trials.json">Ubuntu trial records</a><a href="results/ubuntu-six-runs/samples.jsonl.gz">Ubuntu resource time series</a><a href="results/ubuntu-six-runs/validation.json">Ubuntu audit</a><a href="results/ubuntu-six-runs/host-link.jsonl">Ethernet observations</a><a href="results/ubuntu-deluge-ipv6/study.json">Deluge follow-up registration</a><a href="results/ubuntu-deluge-ipv6/attempts.csv">Deluge follow-up observations</a><a href="results/ubuntu-deluge-ipv6/validation.json">Deluge follow-up audit</a><a href="results/runs/ubuntu-deluge-interface-observer-diagnostic/invalidated.json">Excluded observer diagnostic</a><a href="compose.deluge-ipv6.yaml">Deluge interface overlay</a><a href="compose.ubuntu.yaml">Ubuntu Compose overlay</a><a href="ubuntu/source.json">Official torrent provenance</a></div>
<h3>Upstream release references</h3><div class="source-list"><a href="https://www.qbittorrent.org/download">qBittorrent</a><a href="https://pypi.org/project/deluge/2.2.0/">Deluge 2.2.0</a><a href="https://github.com/transmission/transmission/releases/tag/4.1.4">Transmission 4.1.4</a><a href="https://github.com/rakshasa/rtorrent/releases/tag/v0.16.27">rTorrent 0.16.27</a><a href="https://github.com/ikatson/rqbit/releases/tag/v9.1.0">rqbit 9.1.0</a><a href="https://github.com/aria2/aria2/releases/tag/release-1.37.0">aria2 1.37.0</a></div><p class="resources-note">The initial five versions were resolved on 2026-11-02; aria2 was added on 2026-11-03. This page reports that pinned run; it does not check for newer releases when opened.</p></section>
</main></div>
<footer><span>Synthetic ×3 · Public main ×6 + Deluge interface ×6 · Measured 2026-11-02–03</span><a href="#">Back to top ↑</a></footer>
<script type="application/json" id="chart-data">''' + json.dumps([{k:r[k] for k in ('client','workload','median_mib_s','min_mib_s','max_mib_s')} for r in rows if r['workload'].startswith('download-') or r['workload']=='upload-2-peers'],separators=(',',':')) + '''</script>
<script>
(() => {
  'use strict';
  const names = {qbittorrent:'qBittorrent',deluge:'Deluge',transmission:'Transmission',rtorrent:'rTorrent',rqbit:'rqbit',aria2:'aria2'};
  const data = JSON.parse(document.getElementById('chart-data').textContent);
  const selector = document.getElementById('workload');
  document.getElementById('chart-control').hidden = false;
  selector.addEventListener('change', () => {
    const rows = data.filter(row => row.workload === selector.value);
    const ceiling = Math.max(...rows.map(row => Number(row.max_mib_s)));
    const best = Math.max(...rows.map(row => Number(row.median_mib_s)));
    const bars = document.getElementById('chart-bars');
    const fragment = document.createDocumentFragment();
    rows.forEach(row => {
      const median = Number(row.median_mib_s), low = Number(row.min_mib_s), high = Number(row.max_mib_s);
      const bar = document.createElement('div');
      bar.className = 'bar-row';
      const name = document.createElement('span');
      name.className = 'bar-name';
      name.textContent = names[row.client];
      const track = document.createElement('div');
      track.className = 'bar-track';
      track.setAttribute('aria-hidden','true');
      const fill = document.createElement('span');
      fill.className = 'bar-fill' + (median === best ? ' best' : '');
      fill.style.width = (median / ceiling * 100) + '%';
      const range = document.createElement('span');
      range.className = 'bar-range';
      range.style.left = (low / ceiling * 100) + '%';
      range.style.width = ((high - low) / ceiling * 100) + '%';
      track.append(fill, range);
      const number = document.createElement('span');
      number.className = 'bar-number';
      const value = document.createElement('strong');
      value.textContent = median.toFixed(1);
      const bounds = document.createElement('small');
      bounds.textContent = low.toFixed(1) + '–' + high.toFixed(1);
      number.append(value, bounds);
      bar.append(name, track, number);
      fragment.append(bar);
    });
    bars.replaceChildren(fragment);
    document.getElementById('chart-title').textContent = selector.selectedOptions[0].textContent;
  });
  const filter = document.getElementById('client-filter');
  const publicMetric = document.getElementById('public-metric');
  document.getElementById('public-chart-control').hidden = false;
  publicMetric.addEventListener('change', () => {
    document.querySelectorAll('.public-panel').forEach(panel => {
      panel.hidden = panel.dataset.metric !== publicMetric.value;
    });
  });
  const measurements = [...document.querySelectorAll('#measurements tbody tr')];
  document.getElementById('measurement-control').hidden = false;
  filter.addEventListener('change', () => {
    measurements.forEach(row => { row.hidden = filter.value !== 'all' && row.dataset.client !== filter.value; });
    document.getElementById('row-count').textContent = measurements.filter(row => !row.hidden).length + ' of 60 groups';
  });
})();
</script>
</body>
</html>
'''
page = page.replace('MEASUREMENT_NUMBER', f'{len(sections):02d}').replace('EVIDENCE_NUMBER', f'{len(sections)+1:02d}')
(root / 'index.html').write_text(page)
print(f'Wrote index.html: {len(page):,} characters; {len(sections)} narrative sections; {len(measurements)} measurement rows.')
