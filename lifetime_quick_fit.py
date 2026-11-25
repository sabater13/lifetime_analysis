#!/usr/bin/env python3
"""Pool segments from multiple FLOW files and run a single electron lifetime fit.
This requires the nearline repo.

- for single file:
  python3 lifetime_quick_fit.py /path/to/file1.FLOW.hdf5 /path/to/file2.FLOW.hdf5 ... \
      --output-plot /pscratch/sd/e/esabater/2x2_lifetime/lifetime_analysis/lifetime_quick_fit.png \
      --output-json  /pscratch/sd/e/esabater/2x2_lifetime/lifetime_analysis/lifetime_quick_fit.json

- for multiple files in a directory:
  python3 lifetime_quick_fit.py \
      '/global/cfs/cdirs/dune/www/data/2x2/nearline_run3/flowed_charge/Operations/20261102-*/*.FLOW.hdf5' \
      --output-plot /pscratch/sd/e/esabater/2x2_lifetime/lifetime_analysis/lifetime_quick_fit.png \
      --output-json  /pscratch/sd/e/esabater/2x2_lifetime/lifetime_analysis/lifetime_quick_fit.json
"""

import argparse
import glob
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from scipy.optimize import curve_fit

import h5py
import numpy as np


REPO = Path('/pscratch/sd/e/esabater/2x2_lifetime/arcube_nearline')
sys.path.insert(0, str(REPO / 'actions' / 'lifetime'))
sys.path.insert(0, str(REPO))

from lifetime import LEGACY_SAMPLE, SPLIT_SAMPLES, valid_segments


def gather_segments(paths, dset_key):
    arrays = []
    n_files = 0
    for p in paths:
        try:
            with h5py.File(p, 'r') as f:
                if dset_key not in f:
                    print(f'  skip (no {dset_key}): {Path(p).name}')
                    continue
                arr = f[dset_key][:]
                arrays.append(arr)
                n_files += 1
                print(f'  +{len(arr):4d} segments  {Path(p).name}')
        except Exception as exc:
            print(f'  ERROR {Path(p).name}: {exc}')
    if not arrays:
        raise RuntimeError(f'No files contained {dset_key!r}')
    total = sum(len(a) for a in arrays)
    print(f'\nTotal: {total} segments from {n_files} files')
    return np.concatenate(arrays), n_files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='+', help='FLOW HDF5 paths or a single quoted glob pattern')
    ap.add_argument('--output-plot', required=True)
    ap.add_argument('--output-json', required=True)
    ap.add_argument('--label', default='all_mip')
    ap.add_argument('--window-start', default=None, help='ISO8601 UTC start of the data window (from bash driver)')
    ap.add_argument('--window-end', default=None, help='ISO8601 UTC end of the data window (from bash driver)')
    args = ap.parse_args()

    # expand globs
    paths = []
    for f in args.files:
        expanded = sorted(glob.glob(f))
        paths.extend(expanded if expanded else [f])
    paths = sorted(set(paths))
    print(f'Found {len(paths)} FLOW files\n')
    if not paths:
        sys.exit('ERROR: no files matched')

    # detect which dataset path to use from the first file
    dset_key = None
    with h5py.File(paths[0], 'r') as f:
        for label, path in SPLIT_SAMPLES:
            if path in f and args.label == label:
                dset_key = path
                break
        if dset_key is None and LEGACY_SAMPLE[1] in f:
            dset_key = LEGACY_SAMPLE[1]
        if dset_key is None:
            for label, path in SPLIT_SAMPLES:
                if path in f:
                    dset_key = path
                    args.label = label
                    break
    if dset_key is None:
        sys.exit('ERROR: cannot determine segment dataset path from first file')
    print(f'Using dataset: {dset_key}\n')

    segments_raw, n_files = gather_segments(paths, dset_key)
    segments = valid_segments(segments_raw)
    print(f'Valid segments after cuts: {len(segments)}\n')

    # langau fit
    import lifetime_funcs as LT

    if args.window_end:
        timestamp_str = datetime.fromisoformat(args.window_end.replace('Z', '+00:00')).isoformat()
    elif args.window_start:
        t0 = datetime.fromisoformat(args.window_start.replace('Z', '+00:00'))
        timestamp_str = t0.isoformat()
    else:
        timestamp_str = datetime.now(timezone.utc).isoformat()
    title = f'{timestamp_str} ({args.label})  [{n_files} files pooled]'

    lifetime, lifetime_error, fig = LT.langau_lifetime(
        nhits=segments['nhits'] / segments['dx'],
        dqdx=segments['dQ'] / segments['dx'],
        time_drifted=segments['t'],
        time_bins=np.linspace(0, 1960, 20),
        dqdx_bins=np.linspace(0, 250, 70),
        nhits_bins=np.linspace(0, 30, 42),
        wanted_title=title,
    )
    lifetime = float(lifetime)
    lifetime_error = float(lifetime_error)

    print(f'\n{"="*55}')
    print(f'  Lifetime      : {lifetime:.1f} ± {lifetime_error:.1f} µs')
    print(f'  n_segments    : {len(segments)}')
    print(f'  n_files pooled: {n_files}')
    print(f'{"="*55}\n')

    # append lifetime to a file with the time of the measurement
    timeseries_path = Path(args.output_json).parent.parent / 'lifetime_timeseries.json'
    entry = dict(timestamp=timestamp_str, lifetime_us=lifetime, error_us=lifetime_error,
                 n_segments=int(len(segments)), n_files=n_files)
    if timeseries_path.exists():
        timeseries = json.loads(timeseries_path.read_text())
    else:
        timeseries = []
    timeseries.append(entry)
    timeseries_path.write_text(json.dumps(timeseries, indent=2))
    print(f'Time-series log → {timeseries_path}')

    import matplotlib
    matplotlib.use('Agg')
    fig.savefig(args.output_plot, dpi=150, bbox_inches='tight')
    print(f'Plot → {args.output_plot}')

    # save JSON
    diagnostics = getattr(fig, 'lifetime_diagnostics', {})
    result = dict(
        timestamp=timestamp_str,
        sample=args.label,
        method='track',
        calculation_source='flow_segments_pooled',
        n_files_pooled=n_files,
        n_segments=int(len(segments)),
        segments_dset=dset_key,
        lifetime_us=lifetime,
        error_us=lifetime_error,
        fit_diagnostics=diagnostics,
    )
    Path(args.output_json).write_text(json.dumps(result, indent=2))
    print(f'JSON → {args.output_json}')

    # data / fit ratio
    diag = result['fit_diagnostics']
    t_all  = np.array(diag['drift_time_us'])
    mpv_all = np.array([v if v is not None else np.nan for v in diag['mpv']])
    err_all = np.array([v if v is not None else np.nan for v in diag['mpv_error']])
    fitted_idx = np.array(diag['fitted_bins'])
    t_fit  = t_all[fitted_idx]
    mpv_fit = mpv_all[fitted_idx]
    err_fit = err_all[fitted_idx]

    A   = diag['candidate_parameters']['amplitude']
    tau = diag['candidate_parameters']['lifetime_us']

    def exp_model(t, A, tau):
        return A * np.exp(-t / tau)

    fit_at_bins = exp_model(t_fit, A, tau)
    ratio       = mpv_fit / fit_at_bins
    ratio_err   = err_fit / fit_at_bins

    # fit to central bins
    mask = (t_fit >= 40) & (t_fit <= 180)
    t_c, mpv_c, err_c = t_fit[mask], mpv_fit[mask], err_fit[mask]
    
    # Re-fit to the central window
    p0 = [A, tau]
    try:
        popt, pcov = curve_fit(
            exp_model, t_c, mpv_c,
            sigma=err_c, absolute_sigma=True,
            p0=p0,
        )
        A_c, tau_c = popt
        tau_c_err = np.sqrt(pcov[1, 1])
    except RuntimeError:
        A_c, tau_c, tau_c_err = A, tau, float('nan')
    
    fit_at_bins = exp_model(t_c, A_c, tau_c)
    ratio       = mpv_c / fit_at_bins
    ratio_err   = err_c / fit_at_bins

    fig2, (ax_main, ax_ratio) = plt.subplots(
        2, 1, figsize=(8, 7), sharex=True,
        gridspec_kw={'height_ratios': [3, 1], 'hspace': 0.05}
    )

    t_smooth = np.linspace(t_fit[0], t_fit[-1], 500)
    ax_main.plot(t_smooth, exp_model(t_smooth, A_c, tau_c), color='orange',
                 label=f'$\\tau = {tau_c:.1f}$ µs,  $A = {A_c:.3f}$')
    ax_main.errorbar(t_fit, mpv_fit, yerr=err_fit,
                     fmt='o', color='black', label='Fitted bins', zorder=3)
    ax_main.set_ylabel('MPV of (dN/dx · dQ/dx)')
    ax_main.legend(fontsize=9)
    ax_main.grid(axis='both', linestyle='--', alpha=0.5)
    ax_main.set_title(f'Pooled fit  ({n_files} files,  {len(segments)} segments,  '
                      f'χ²/ndf = {diag["chi2_ndf"]:.2f})')

    # ratio
    ax_ratio.axhline(1.0, color='blue', linewidth=1, alpha=0.7)
    #ax_ratio.fill_between(t_fit, 0.9, 1.1, color='orange', alpha=0.12, label='±10%')
    ax_ratio.errorbar(t_c, ratio, yerr=ratio_err, fmt='o', color='black', zorder=3)
    ax_ratio.set_ylabel('Data / Fit')
    ax_ratio.set_xlabel('Time Drifted [µs]')
    ax_ratio.set_ylim(0.7, 1.3)
    #ax_ratio.legend(fontsize=8, loc='upper right')
    ax_ratio.grid(axis='both', linestyle='--', alpha=0.5)

    ratio_plot = Path(args.output_plot).with_stem(Path(args.output_plot).stem + '_ratio')
    fig2.savefig(ratio_plot, dpi=150, bbox_inches='tight')
    plt.close(fig2)
    print(f'Ratio plot → {ratio_plot}')


if __name__ == '__main__':
    main()