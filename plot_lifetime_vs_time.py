#!/usr/bin/env python3
"""Read all per-hour lifetime JSON files and plot lifetime vs. time.

Usage:
    python3 plot_lifetime_vs_time.py \
        --json-dir /pscratch/sd/e/esabater/2x2_lifetime/lifetime_analysis/lifetime_hourly/jsons \
        --output   /pscratch/sd/e/esabater/2x2_lifetime/lifetime_analysis/lifetime_vs_time.png
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np


def load_jsons(json_dir: Path):
    """Return a list of dicts sorted by timestamp from all JSON files in json_dir."""
    records = []
    for path in sorted(json_dir.glob('lifetime_*.json')):
        try:
            data = json.loads(path.read_text())
        except Exception as exc:
            print(f'  skip {path.name}: {exc}')
            continue

        # required fields
        try:
            ts   = datetime.fromisoformat(data['timestamp'])
            lt   = float(data['lifetime_us'])
            err  = float(data['error_us'])
        except (KeyError, ValueError) as exc:
            print(f'  skip {path.name}: missing field – {exc}')
            continue

        records.append(dict(
            timestamp=ts,
            lifetime_us=lt,
            error_us=err,
            n_segments=data.get('n_segments', 0),
            n_files=data.get('n_files_pooled', data.get('n_files', 0)),
            label=path.stem,          # e.g. lifetime_20261103_2100
        ))

    records.sort(key=lambda r: r['timestamp'])
    return records


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json-dir', required=True,
                    help='Directory containing per-hour lifetime_*.json files')
    ap.add_argument('--output', required=True,
                    help='Output PNG path')
    ap.add_argument('--title', default='Electron lifetime evolution (1-hour windows)',
                    help='Plot title')
    args = ap.parse_args()

    json_dir = Path(args.json_dir)
    if not json_dir.is_dir():
        sys.exit(f'ERROR: {json_dir} is not a directory')

    records = load_jsons(json_dir)
    if not records:
        sys.exit('ERROR: no valid JSON files found')

    print(f'Loaded {len(records)} windows')
    for r in records:
        print(f"  {r['timestamp'].isoformat()}  "
              f"{r['lifetime_us']:.1f} ± {r['error_us']:.1f} µs  "
              f"({r['n_segments']} segs, {r['n_files']} files)")

    times    = [r['timestamp'] for r in records]
    lifetimes = np.array([r['lifetime_us'] for r in records])
    errors    = np.array([r['error_us']    for r in records])

    fig, ax = plt.subplots(figsize=(12, 5))

    ax.errorbar(
        times, lifetimes, yerr=errors,
        fmt='o-', color='steelblue', ecolor='steelblue',
        capsize=4, linewidth=1.5, markersize=6, label='Lifetime (1-hr window)',
    )

    # shade ±1σ band
    #ax.fill_between(
        #times,
        #lifetimes - errors,
        #lifetimes + errors,
        #color='steelblue', alpha=0.15,
    #)

    # horizontal reference lines (optional, adjust as needed)
    for ref, style, lbl in [
        (100, dict(color='gray',   linestyle='--', linewidth=1, alpha=0.5), '100 µs'),
        (250, dict(color='orange', linestyle='--', linewidth=1, alpha=0.5), '250 µs'),
    ]:
        ax.axhline(ref, **style, label=lbl)

    # total_hours = (times[-1] - times[0]).total_seconds() / 3600
    # if total_hours <= 6:
    #     major_locator = mdates.HourLocator(interval=1, tz=timezone.utc)
    # elif total_hours <= 24:
    #     major_locator = mdates.HourLocator(interval=2, tz=timezone.utc)
    # else:
    #     major_locator = mdates.HourLocator(interval=4, tz=timezone.utc)
    
    major_locator = mdates.HourLocator(interval=10, tz=timezone.utc)
    
    ax.xaxis.set_major_locator(major_locator)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m\n%H:%M', tz=timezone.utc))

    # Force all tick labels to be visible (autofmt_xdate can hide them)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=0, ha='center', visible=True)

    # Add a small margin so the first/last points aren't clipped against the axis edge
    ax.margins(x=0.03)

    ax.set_xlabel('Time (UTC)')
    ax.set_ylabel('Electron lifetime [µs]')
    ax.set_title(args.title)
    ax.legend(fontsize=9)
    ax.grid(axis='both', linestyle='--', alpha=0.4)
    ax.set_ylim(bottom=0)

    # annotate number of segments per point
    #for r in records:
        #ax.annotate(
            #f"{r['n_segments']//1000}k",
            #xy=(r['timestamp'], r['lifetime_us'] + r['error_us']),
            #xytext=(0, 5), textcoords='offset points',
            #ha='center', fontsize=7, color='steelblue',
        #)

    fig.tight_layout()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches='tight')
    print(f'\nPlot → {out}')


if __name__ == '__main__':
    main()