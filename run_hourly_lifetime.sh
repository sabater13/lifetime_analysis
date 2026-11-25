# #!/bin/bash
# Run a pooled electron lifetime fit for each 1-hour window from a start time
# to the latest available files, writing one JSON and one plot per window.
#
# Usage:
#   bash run_hourly_lifetime.sh
#
# Time range: 2026-11-03 21:00 UTC  →  now (script end time)
# Input directory scanned for packet-*.FLOW.hdf5 files.
INPUT_DIR_03="/global/cfs/cdirs/dune/www/data/2x2/nearline_run3/flowed_charge/Operations/20261122-phase2-beam"
INPUT_DIR_04="/global/cfs/cdirs/dune/www/data/2x2/nearline_run3/flowed_charge/Operations/20261122-phase2-beam_v2"
INPUT_DIR_05="/global/cfs/cdirs/dune/www/data/2x2/nearline_run3/flowed_charge/Operations/20261122-phase2-beam_v2"
INPUT_DIR_06="/global/cfs/cdirs/dune/www/data/2x2/nearline_run3/flowed_charge/Operations/20261123-phase2-beam"

OUTPUT_DIR="/pscratch/sd/e/esabater/2x2_lifetime/lifetime_analysis/lifetime_hourly"

SCRIPT="$(dirname "$0")/lifetime_quick_fit.py"

mkdir -p "$OUTPUT_DIR/plots"
mkdir -p "$OUTPUT_DIR/jsons"

# time window configuration
# Start: 2026-11-03 21:00:00 UTC  (yesterday 9 pm)
WINDOW_START_EPOCH=$(date -u -d "2026-11-03 21:00:00" +%s)
# End: now
WINDOW_END_EPOCH=$(date -u -d "2026-11-04 21:00:00" +%s) #$(date -u +%s)
WINDOW_SIZE=3600 # in seconds

# collect and sort ALL available files
echo "Scanning input directories for FLOW files..."
mapfile -d '' ALL_FILES < <(
    find "$INPUT_DIR_03" "$INPUT_DIR_04" -maxdepth 1 -type f \
        -name "packet-*.FLOW.hdf5" -print0 2>/dev/null | sort -z
)
echo "Found ${#ALL_FILES[@]} total FLOW files (both directories combined)"
echo "  03 dir: $INPUT_DIR_03"
echo "  04 dir: $INPUT_DIR_04"
echo ""

# convert a filename timestamp (YYYY_MM_DD_HH_MM_SS) to epoch seconds
ts_to_epoch() {
    local ts="$1"
    # ts format: YYYY_MM_DD_HH_MM_SS
    local formatted
    formatted=$(echo "$ts" | sed 's/_\([0-9]\{2\}\)_\([0-9]\{2\}\)_\([0-9]\{2\}\)$/ \1:\2:\3/' \
                           | sed 's/_/-/g; s/ /_/')
    # formatted is now YYYY-MM-DD_HH:MM:SS  → pass to date
    date -u -d "${formatted/_/ }" +%s 2>/dev/null || echo 0
}

# loop over 1-hour windows
win_start=$WINDOW_START_EPOCH
n_windows=0

while (( win_start < WINDOW_END_EPOCH )); do
    win_end=$(( win_start + WINDOW_SIZE ))
    # Clamp to now so the label is accurate even for a partial last window
    if (( win_end > WINDOW_END_EPOCH )); then
        win_end=$WINDOW_END_EPOCH
    fi
 
    win_start_str=$(date -u -d "@$win_start" "+%Y-%m-%dT%H:%M:%SZ")
    win_end_str=$(date -u   -d "@$win_end"   "+%Y-%m-%dT%H:%M:%SZ")
    label=$(date -u -d "@$win_start" "+%Y%m%d_%H%M")   # e.g. 20261103_2100
 
    echo "========================================================"
    echo "Window: ${win_start_str}  →  ${win_end_str}"
    echo "========================================================"
 
    # select files whose timestamp falls in [win_start, win_end)
    selected_files=()
    for file in "${ALL_FILES[@]}"; do
        filename=$(basename "$file")
        ts=$(echo "$filename" | grep -oE '[0-9]{4}_[0-9]{2}_[0-9]{2}_[0-9]{2}_[0-9]{2}_[0-9]{2}' || true)
        if [[ -z "$ts" ]]; then
            continue
        fi
        epoch=$(ts_to_epoch "$ts")
        if (( epoch >= win_start && epoch < win_end )); then
            selected_files+=("$file")
        fi
    done
 
    echo "Files in window: ${#selected_files[@]}"
 
    if (( ${#selected_files[@]} == 0 )); then
        echo "  → No files in this window, skipping."
        win_start=$(( win_start + WINDOW_SIZE ))
        echo ""
        continue
    fi
 
    out_plot="$OUTPUT_DIR/plots/lifetime_${label}.png"
    out_json="$OUTPUT_DIR/jsons/lifetime_${label}.json"
 
    echo "Running lifetime fit..."
    python3 "$SCRIPT" "${selected_files[@]}" \
        --output-plot "$out_plot" \
        --output-json "$out_json" \
        --window-start "$win_start_str" \
        --window-end   "$win_end_str" \
        || { echo "  ERROR: fit failed for window $label"; }
 
    n_windows=$(( n_windows + 1 ))
    win_start=$(( win_start + WINDOW_SIZE ))
    echo ""
done
 
echo "========================================================"
echo "Done.  Processed $n_windows non-empty windows."
echo "JSONs → $OUTPUT_DIR/jsons/"
echo "Plots → $OUTPUT_DIR/plots/"
echo "========================================================"